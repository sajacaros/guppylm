# GuppyLM → 한·영 이중언어 MoE 전환 설계

작성일: 2026-06-29

## 목표

영어 전용 ~8.7M 바닐라 트랜스포머인 GuppyLM을 (1) 한국어를 말할 수 있게 하고, (2) 밀집(dense) FFN을
**Mixture-of-Experts(MoE)** 로 교체한다. 데이터 구축부터 평가까지 전 단계가 MoE/이중언어를 위해 어떻게
바뀌는지 설명하는 HTML 문서와, 원격 GPU에서 그대로 실행할 수 있는 실행 가이드를 함께 제공한다.

## 확정 결정

- **언어 범위**: 한·영 이중언어. 입력 언어에 맞춰 응답. 카테고리는 영어와 동일한 60개를 한국어에도 미러링.
- **MoE 방식**: 주류형(Switch/Mixtral 계열). 라우터가 학습으로 토큰을 배분하고 전문화는 창발. 역할 사전배정 없음.
- **전문가 구성**: 전문가 4개, top-2 라우팅. Switch 스타일 부하분산(load-balancing) aux loss.
- **토크나이저**: ByteLevel BPE 유지. vocab 상한 4096 → 8192로 확장(한글 3바이트 음절 수용). 실제 vocab은 데이터에 의해 결정.
- **데이터**: 템플릿 조합 방식 유지. 60주제 전체에 대한 한국어 네이티브 생성기 신규 작성. EN/KO 50:50.
- **구현 범위**: 전체 파이프라인 실제 동작. `config.use_moe` 플래그로 dense↔MoE 전환.
- **학습**: 사용자가 원격 GPU에서 실행. 코드는 올바르게 동작하도록 작성하고 실행과정을 문서화.

## 아키텍처

### MoE 레이어 (`model.py`)

밀집 블록의 단일 FFN을 다음으로 교체한다.

```
            ┌─ Expert0: up(d→h)→ReLU→down(h→d) ┐
 x(d) ─┬──→ ├─ Expert1 … Expert3 (동일 shape)   ├─→ Σ wᵢ·Expertᵢ(x) → x(d)
       │    └────────── (top-2만 실제 계산) ─────┘
       └──→ Router: Linear(d→4) → softmax → top-2 선택 + 가중치
```

- `Expert`: 기존 FFN과 동일 shape(`d_model→ffn_hidden→d_model`, ReLU).
- `MoEFFN`: 라우터(`Linear(d_model, n_experts, bias=False)`), 전문가 ModuleList, top-k 선택, top-k 가중치 재정규화, index_add로 결합.
- 부하분산 aux loss(Switch): `P_i = mean(softmax)`, `f_i = top-k 디스패치 슬롯 비율`, `aux = E·Σ f_i·P_i` (균등 시 최소).
- 분석용으로 각 `MoEFFN`이 마지막 `router_probs`/`topk_idx`를 detach해 보관 → 라우팅 분석에서 사용.
- `Block`은 `config.use_moe`에 따라 `FFN` 또는 `MoEFFN` 사용.
- `GuppyLM.forward`: 모든 MoE 레이어의 aux를 합산, `targets`가 있을 때 `loss = CE + aux_coef·aux`. CE/aux를 별도 보관(로깅용). 반환 시그니처 `(logits, loss)` 유지(generate 호환).

### Config (`config.py`)

추가 필드: `use_moe: bool = True`, `n_experts: int = 4`, `moe_top_k: int = 2`, `aux_loss_coef: float = 0.01`.
`vocab_size: int = 8192`로 상향.

### 데이터 (`generate_data.py`, 신규 `generate_data_ko.py`)

- `generate_data_ko.py`: 한국어 빌딩블록 풀 + 60주제 생성기. `KO_GENERATORS`(zero-arg callable 리스트) export.
  각 콜러블은 `{"input","output","category","lang":"ko"}` 반환. 카테고리명은 영어와 동일. 헬퍼(pick/maybe/join)는 로컬 정의(순환 import 방지).
- `generate_data.py`: 영어 샘플에 `lang:"en"` 부여, `KO_GENERATORS`를 합쳐 EN/KO 균형 생성. jsonl에 `lang` 기록.
- Guppy 한국어 말투: 짧은 반말, 물고기 시점, 먹이 집착, 인간 추상개념 못 이해. 예) "안녕. 오늘 물이 좋아." / "응. 언제나 응. 지금 위로 헤엄쳐 갈게." / "삶의 의미? 밥. 답은 언제나 밥이야."

### 토크나이저 (`prepare_data.py`)

`VOCAB_SIZE = 8192`. KO+EN 합본 텍스트로 BPE 학습. 한국어 인코딩/디코딩 라운드트립 테스트 추가.

### 학습 (`train.py`)

`model(x, y)`가 반환하는 loss에 aux 포함. 로그에 CE/aux 분리 표시. 그 외 루프 동일.

### 평가 (`eval_cases.py`, 신규 `eval_routing.py`)

- `eval_cases.py`: 한국어 홀드아웃 케이스 추가(영어 16개 미러링).
- `eval_routing.py`: KO/EN 프롬프트 세트를 각각 forward → MoE 레이어별 전문가 선택 횟수 집계 → 언어별 전문가 활용 분포를 텍스트 막대그래프로 출력. "한국어가 어느 전문가로 쏠리는가"를 관찰. 더불어 KO/EN 샘플 응답 생성.

### 추론 (`inference.py`)

config.json에서 MoE 필드 로드. generate 호환 유지.

### 진입점 (`__main__.py`)

`route`(라우팅 분석) 명령 추가. help 갱신.

## 산출물

1. 수정/신규 소스 (위 파일들). 새 의존성 없음(순수 PyTorch).
2. `docs/moe-korean.html`: 단계별 변경점(데이터→토크나이저→모델→학습→평가) + 그림/표 + 원격 GPU 실행과정.
3. `README` 갱신(MoE/한국어 섹션, 실행 명령).

## 비범위(YAGNI)

- 멀티턴, 시스템 프롬프트, 전문가 병렬화(분산), 표현식 라우팅(expert-choice), 공유 전문가(shared expert)는 제외.
- 실제 GPU 학습 실행은 사용자 몫.

## 검증

- `python -m guppylm prepare` → 한/영 데이터 + 8192 토크나이저 생성.
- `python -m guppylm train` → MoE 학습, CE/aux 로그.
- `python -m guppylm route` → 언어별 전문가 라우팅 분포 출력.
- `python -m guppylm chat -p "안녕 구피"` / `-p "hi guppy"` → 각 언어 응답.
- `config.use_moe=False`로 dense 회귀 동작 확인.
