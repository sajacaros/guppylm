# GuppyLM Playground — 정적 브라우저 서빙 페이지 설계

- 날짜: 2026-06-29
- 상태: 승인 대기 (브레인스토밍 → 스펙 리뷰)
- 관련 문서: [[2026-06-29-moe-korean-guppy-design]]

## 목표

한 페이지에서 세 가지를 보여주는 "GuppyLM Playground"를 만든다.

1. **Dense 챗봇** — MoE 없는 클래식 모델
2. **MoE 챗봇** — 한·영 이중언어 MoE 모델
3. **MoE 아키텍처 가이드** — 기존 `docs/moe-korean.html`

추가로, dense·MoE 답변을 같은 질문으로 나란히 비교하는 탭을 덤으로 둔다.

모든 추론은 **브라우저 안에서 ONNX Runtime Web(WASM)** 으로 실행한다. 서버·백엔드·GPU·API 키가 전혀 없고, GitHub Pages 같은 정적 호스팅에 그대로 올라간다. 기존 `docs/index.html`이 이미 dense 모델로 이 방식을 검증해 두었으므로 그 엔진을 재사용·일반화한다.

## 비목표 (YAGNI)

- 백엔드 서버 / REST API — 정적 추론으로 충분.
- 멀티유저, 대화 영속화, 인증.
- 새 모델 학습 — "훈련 끝났다" 가정. 본 작업은 서빙 UI + export 도구.

## 아키텍처

```
docs/
  index.html        ← 탭형 "Playground"로 확장 (단일 페이지)
  moe-korean.html   ← 아키텍처 가이드 (+ WASM 설명 섹션 추가)
  model.onnx        ← dense 모델 (vocab 4096)  [기존]
  tokenizer.json    ← dense tokenizer          [기존]
  model_moe.onnx    ← MoE 모델 (vocab 8192)    [신규, export 필요]
  tokenizer_moe.json← MoE tokenizer            [신규, export 필요]
```

추론 흐름(탭별 동일): `텍스트 → 토크나이저 encode → ONNX forward(반복 생성) → decode → 출력`. 전부 방문자 CPU에서 WASM으로 실행.

## 레이아웃 — 단일 페이지 + 상단 탭

```
┌─────────────────────────────────────────────┐
│ 🐠 GuppyLM Playground            [☀/🌙 테마] │
│ [💬 Dense] [🧠 MoE] [⚖️ 비교] [📐 아키텍처]   │
├─────────────────────────────────────────────┤
│  (선택된 탭 내용)                             │
└─────────────────────────────────────────────┘
```

- **💬 Dense / 🧠 MoE**: 동일한 채팅 UI. 활성 모델만 다름.
- **⚖️ 비교**: 입력 한 번 → dense·MoE 두 칸에 동시 생성, 답변 비교.
- **📐 아키텍처**: `moe-korean.html`을 iframe으로 임베드(+ 새 탭으로 열기 링크).

## 컴포넌트

### 1. 모델 레지스트리 (JS 객체)
각 모델의 메타데이터를 한 곳에 선언해 엔진이 참조한다.

```js
const MODELS = {
  dense: { label: "Dense", model: "model.onnx",     tokenizer: "tokenizer.json",     vocab: 4096 },
  moe:   { label: "MoE",   model: "model_moe.onnx", tokenizer: "tokenizer_moe.json", vocab: 8192 },
};
```

### 2. 채팅 엔진 (기존 index.html 로직 일반화)
현재 전역 `session`/`tokenizer` 하나만 다루는 코드를 **모델 id로 인덱싱한 맵**으로 바꾼다.

- `loadModel(id)` — 해당 모델+토크나이저를 lazy-load 후 캐시. 탭 처음 열 때만 다운로드.
- `generate(id, prompt)` — 그 모델로 생성. 비교 탭은 두 id를 병렬 호출.
- 토크나이저 빌더(ByteLevel BPE)는 그대로 재사용 — vocab만 다르면 됨.

### 3. 탭 컨트롤러
순수 클라이언트 사이드. 탭 클릭 → 해당 패널 표시 + 모델 lazy-load. 추가 의존성 없음.

### 4. 우아한 degrade
`model_moe.onnx` fetch가 404면 MoE/비교 탭에서 **"MoE 모델을 export하면 활성화됩니다"** 안내 + export 명령을 보여준다(에러로 죽지 않음).

## 모델 아티팩트 & export 도구

`tools/export_onnx.py`를 dense·MoE 둘 다 내보낼 수 있게 조정한다.

- 출력 파일명을 인자로(`--output docs/model_moe.onnx`), 토크나이저 복사 대상도 파일명 맞춤(`tokenizer_moe.json`).
- 사용 예:
  ```bash
  # dense
  python tools/export_onnx.py --checkpoint checkpoints/dense.pt \
      --tokenizer data/tokenizer.json --output docs/model.onnx
  # MoE
  python tools/export_onnx.py --checkpoint checkpoints/best_model.pt \
      --tokenizer data/tokenizer.json --output docs/model_moe.onnx
  ```

### MoE ONNX export 리스크 (핵심 미검증 지점)
`MoEFFN.forward`는 `torch.topk` → `nonzero` → `index_add_`를 expert 루프에서 쓴다. 이 동적 연산이 ONNX/onnxruntime-web에서 안 돌 수 있다.

- **검증**: 랜덤 가중치 MoE 모델로 `torch.onnx.export` → onnxruntime로 forward가 되는지 먼저 확인(가중치 학습 여부와 무관하게 그래프 차원에서 검증 가능).
- **실패 시 대안**: 추론 전용 export 경로에서 "모든 expert 계산 후 top-k 마스킹"으로 forward를 바꾼다(수학적으로 동일, 정적 그래프라 export 친화적, 9M 규모라 비용 무시 가능). 학습 경로는 기존 희소 버전 유지.
- torch 미설치 환경이라 이 검증은 사용자 환경(또는 별도 설치)에서 실행. 안 되면 위 대안을 적용/안내.

## moe-korean.html — WASM 설명 섹션 추가

새 섹션 "브라우저 안에서 모델 돌리기 — WASM"을 적절한 위치(실행/배포 부근)에 추가. 내용 개요:

1. WebAssembly란 — 브라우저 내장, 네이티브급 속도의 바이너리 형식. JS는 로직, WASM은 무거운 계산.
2. onnxruntime-web = ONNX Runtime(C++)을 WASM으로 컴파일 → 서버 추론 엔진이 브라우저 탭에서 그대로 동작.
3. index.html의 실제 흐름(fetch model+tokenizer → WASM forward → 생성 루프) 다이어그램.
4. 장점(서버 0원·프라이버시·오프라인) / 한계(방문자 CPU, 소형 모델만).

기존 `moe-korean.html`의 스타일(`.box`, 코드 블록, 섹션 헤더 `<h2><span class="n">`)을 그대로 따른다.

## 테스트 / 검증

- 정적 페이지라 단위 테스트 프레임워크 없음. 검증은 수동 + export 스모크 테스트.
- **export 스모크**: 랜덤 가중치 dense·MoE 모델 export → onnxruntime로 1-스텝 forward 성공 확인.
- **프론트**: 로컬 정적 서버로 띄워 각 탭 로드, dense 챗 동작, MoE 부재 시 degrade 동작 확인.
- 회귀: 기존 dense 챗 동작이 깨지지 않을 것(같은 엔진 재사용).

## 작업 범위 요약

1. `docs/index.html` → 탭형 Playground로 확장 (4탭, 모델 레지스트리, 엔진 일반화, degrade).
2. `tools/export_onnx.py` → 출력/토크나이저 파일명 파라미터화, MoE export 지원.
3. (필요 시) `model.py`에 export 친화적 MoE inference forward 경로.
4. `docs/moe-korean.html` → WASM 브라우저 추론 설명 섹션 추가.

## 열린 리스크

- MoE의 ONNX-web 호환성(위 대안으로 완화).
- MoE 체크포인트/토크나이저 실제 보유 여부 — 없으면 UI는 degrade로 동작, 모델은 사용자가 export.
- 비교 탭은 "A" 핵심 3탭에 대한 덤. 불필요하면 제거(범위 축소 용이).
