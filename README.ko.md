<p align="center">
  <img src="assets/guppy.png" alt="GuppyLM" width="400"/>
</p>

<h1 align="center">GuppyLM</h1>
<p align="center"><em>작은 물고기처럼 말하는 약 900만 파라미터짜리 LLM.</em></p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇬🇧-English-0891b2" alt="English README"/></a>
  <br/>
  <a href="https://huggingface.co/datasets/arman-bd/guppylm-60k-generic"><img src="https://img.shields.io/badge/🤗_Dataset-guppylm--60k-blue" alt="Dataset"/></a>&nbsp;
  <a href="https://huggingface.co/arman-bd/guppylm-9M"><img src="https://img.shields.io/badge/🤗_Model-guppylm--9M-orange" alt="Model"/></a>&nbsp;
  <a href="https://github.com/arman-bd/guppylm/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="License"/></a>
  <br/>
  <a href="https://colab.research.google.com/github/arman-bd/guppylm/blob/main/train_guppylm.ipynb"><img src="https://img.shields.io/badge/Train_in-Colab-F9AB00?logo=googlecolab" alt="Train"/></a>&nbsp;
  <a href="https://colab.research.google.com/github/arman-bd/guppylm/blob/main/use_guppylm.ipynb"><img src="https://img.shields.io/badge/Chat_in-Colab-F9AB00?logo=googlecolab" alt="Chat"/></a>
  <br/>
  <a href="https://arman-bd.github.io/guppylm/"><img src="https://img.shields.io/badge/Try_in-Browser-64ffda?style=for-the-badge&logo=webassembly&logoColor=white" alt="Browser Demo"/></a>
</p>

---

> **이 프로젝트는 "나만의 언어 모델을 학습시키는 것은 마법이 아니다"라는 것을 보여주기 위해 존재합니다.**
> 박사 학위도, 거대한 GPU 클러스터도 필요 없습니다. Colab 노트북 하나, 5분이면 데이터 생성·토크나이저·모델 구조·학습 루프·추론까지 처음부터 직접 만든 LLM이 완성됩니다. 노트북을 실행할 줄 안다면, 언어 모델도 학습시킬 수 있습니다.
>
> 에세이를 써내는 수십억 파라미터 모델을 만들어주지는 않습니다. 하지만 원시 텍스트에서 학습된 가중치, 그리고 생성된 출력에 이르기까지 모든 조각이 어떻게 작동하는지를 정확히 보여주어, 거대 모델이 더 이상 블랙박스처럼 느껴지지 않게 해줍니다.

---

> 아래 대화는 모델의 실제 출력입니다. GuppyLM은 **영어로만** 학습되었으므로 영어로 대화합니다.

```
You> hi guppy
Guppy> hi there. i just found a nice spot near the rock. the temperature feels nice.

You> are you hungry
Guppy> yes. always yes. i will swim to the top right now. i promise to eat all of it.

You> do you like bubbles
Guppy> i love bubbles. they make the water feel slightly different.

You> what is the meaning of life
Guppy> food. the answer is always food.

You> tell me a joke
Guppy> what did the fish say when it hit the wall. dam.

You> do you love me
Guppy> you're my favorite big shape. my mouth are happy when you're here.

You> goodnight guppy
Guppy> ok sleep time. i was following a bubble but now i'll stop. goodnight tank. goodnight water.
```

---

## GuppyLM이란?

GuppyLM은 `Guppy`라는 이름의 물고기인 척하는 아주 작은 언어 모델입니다. 물, 먹이, 빛, 수조 생활에 대해 짧고 소문자로 된 문장으로 이야기합니다. 돈, 전화기, 정치 같은 인간의 추상적 개념은 이해하지 못하며 — 이해하려고 하지도 않습니다.

60개 주제에 걸친 6만 건의 합성 대화로 처음부터 학습되었고, 단일 GPU에서 약 5분 만에 학습되며, 브라우저에서 돌아갈 만큼 작은 모델을 만들어냅니다.

---

## 아키텍처

| | |
|---|---|
| **파라미터** | 8.7M |
| **레이어** | 6 |
| **히든 차원** | 384 |
| **헤드** | 6 |
| **FFN** | 768 (ReLU) |
| **Vocab** | 2,418 (BPE · 설정 상한 4,096) |
| **최대 시퀀스** | 128 토큰 |
| **정규화** | LayerNorm |
| **위치 인코딩** | 학습형 임베딩 |
| **LM 헤드** | 임베딩과 가중치 공유(weight-tied) |

평범한 바닐라 트랜스포머입니다. GQA, RoPE, SwiGLU, early exit 같은 것은 없습니다. 가능한 한 단순하게 만들었습니다.

> **참고:** `vocab_size`는 설정상 4,096이 상한이지만, 작은 영어 코퍼스에 `min_frequency=2`로 BPE를 학습한 결과 실제 vocab은 **2,418개**입니다. 배포된 `tokenizer.json`이 이 값을 갖습니다.

---

## 🐟 한·영 MoE 버전

영어 전용 dense 모델을 **한국어도 말하는 Mixture-of-Experts** 모델로 확장한 버전입니다. 단계별로 무엇이 어떻게 바뀌는지는 **[`docs/moe-korean.html`](docs/moe-korean.html)** 에 그림·코드와 함께 정리돼 있습니다.

| | dense (원본) | MoE (이 버전) |
|---|---|---|
| FFN | 블록당 1개 | **전문가 4개 + 라우터, top-2** |
| 언어 | 영어 | **한·영 이중언어 (50:50)** |
| Vocab 상한 | 4,096 | **8,192** (한글 음절 수용) |
| 파라미터 | 10.3M | **20.9M 전체 / 13.9M 활성(토큰당)** |
| 손실 | CE | **CE + 부하분산 aux loss** |

- **라우팅은 학습형**입니다 (Switch/Mixtral 방식). 전문가에 역할을 배정하지 않고, 학습 중 분화가 **창발**합니다.
- `config.use_moe = False`로 두면 기존 dense 모델로 되돌아가 직접 비교할 수 있습니다.
- 한국어 데이터는 번역이 아니라 `generate_data_ko.py`의 **네이티브 한국어 템플릿**(60주제)으로 생성합니다.

```bash
python -m guppylm prepare    # 한·영 데이터 + 8192 토크나이저
python -m guppylm train      # MoE 학습 (로그에 Aux 컬럼)
python -m guppylm route      # 한·영이 어느 전문가로 가는지 분석 ← MoE 하이라이트
python -m guppylm chat -p "안녕 구피"
python -m guppylm chat -p "hi guppy"
```

> 📖 문서 두 종:
> - **[docs/tutorial.html](docs/tutorial.html)** — 명령어를 따라 치며 직접 돌려보는 **따라하기**
> - **[docs/moe-korean.html](docs/moe-korean.html)** — 단계별 변경점·설계 Q&A **개념/레퍼런스**

---

## 성격

Guppy는:
- 짧고 소문자로 된 문장으로 말합니다
- 세상을 물, 온도, 빛, 진동, 먹이를 통해 경험합니다
- 인간의 추상적 개념을 이해하지 못합니다
- 친근하고, 호기심 많고, 약간 멍청합니다
- 먹이 생각을 아주 많이 합니다

**60개 주제:** 인사, 감정, 온도, 먹이, 빛, 물, 수조, 소음, 밤, 외로움, 거품, 유리, 반사, 호흡, 수영, 색깔, 맛, 식물, 필터, 이끼, 달팽이, 두려움, 신남, 지루함, 호기심, 행복, 피곤함, 바깥세상, 고양이, 비, 계절, 음악, 방문객, 아이들, 삶의 의미, 시간, 기억, 꿈, 크기, 미래, 과거, 이름, 날씨, 잠, 친구, 농담, 공포, 사랑, 나이, 지능, 건강, 노래, TV 등.

---

## 빠른 시작

### 브라우저에서 사용해보기 (설치 불필요)

[![Try in Browser](https://img.shields.io/badge/Try_in-Browser-64ffda?logo=webassembly)](https://arman-bd.github.io/guppylm/)

WebAssembly를 통해 브라우저 안에서 완전히 실행됩니다. 양자화된 ONNX 모델(약 10MB)을 내려받아 로컬에서 추론합니다 — 서버도, API 키도 없습니다.

### Colab에서 Guppy와 대화하기

[![Open in Colab](https://img.shields.io/badge/Chat_in-Colab-F9AB00?logo=googlecolab)](https://colab.research.google.com/github/arman-bd/guppylm/blob/main/use_guppylm.ipynb)

HuggingFace에서 사전 학습된 모델을 내려받아 대화할 수 있습니다. 모든 셀을 실행하기만 하면 됩니다.

### 직접 학습하기

[![Open in Colab](https://img.shields.io/badge/Train_in-Colab-F9AB00?logo=googlecolab)](https://colab.research.google.com/github/arman-bd/guppylm/blob/main/train_guppylm.ipynb)

1. 런타임을 **T4 GPU**로 설정합니다
2. **모든 셀 실행** — 데이터셋 내려받기, 토크나이저 학습, 모델 학습, 테스트까지 자동 진행됩니다
3. HuggingFace에 업로드하거나 로컬로 내려받습니다

### 로컬에서 대화하기

```bash
pip install torch tokenizers

# 사전 학습된 모델을 먼저 내려받습니다 (직접 학습하지 않은 경우)
python -m guppylm download

python -m guppylm chat
```

```
You> the cat is looking at you
Guppy> i hide behind the plant when the furry one comes.

You> it is raining outside
Guppy> i think rain is the best thing about outside.
```

대화형 채팅 모드에서는 대화가 누적되면서 128 토큰 한계에 금방 도달해 품질이 떨어집니다.
단일 프롬프트로 호출해 응답 후 바로 종료할 수도 있습니다:

```bash
python -m guppylm chat --prompt "tell me a joke"
```

---

## 데이터셋

HuggingFace의 **[arman-bd/guppylm-60k-generic](https://huggingface.co/datasets/arman-bd/guppylm-60k-generic)** 입니다.

| | |
|---|---|
| 샘플 수 | 60,000 (학습 57K / 테스트 3K) |
| 형식 | `{"input": "...", "output": "...", "category": "..."}` |
| 카테고리 | 60 |
| 생성 방식 | 합성 템플릿 조합 |

```python
from datasets import load_dataset
ds = load_dataset("arman-bd/guppylm-60k-generic")
print(ds["train"][0])
# {'input': 'hi guppy', 'output': 'hello. the water is nice today.', 'category': 'greeting'}
```

---

## 프로젝트 구조

```
guppylm/
├── config.py               하이퍼파라미터 (모델 + 학습)
├── model.py                바닐라 트랜스포머
├── dataset.py              데이터 로딩 + 배치 구성
├── train.py                학습 루프 (코사인 LR, AMP)
├── generate_data.py        대화 데이터 생성기 (60개 주제)
├── eval_cases.py           홀드아웃 테스트 케이스
├── prepare_data.py         데이터 준비 + 토크나이저 학습
└── inference.py            채팅 인터페이스

tools/
├── make_colab.py           Colab 노트북 생성
├── export_onnx.py          모델을 ONNX로 내보내기 (uint8 양자화)
├── export_dataset.py       데이터셋을 HuggingFace에 업로드
└── dataset_card.md         HuggingFace 데이터셋 README

docs/
├── index.html              브라우저 데모 (ONNX + WASM)
├── download.sh             HF에서 model.onnx + tokenizer 내려받기
├── model.onnx              uint8 양자화 모델 (약 10MB)
├── tokenizer.json          BPE 토크나이저
└── guppy.png               로고 (투명 배경)
```

---

## 설계 결정

**왜 시스템 프롬프트가 없나요?** 모든 학습 샘플이 동일한 시스템 프롬프트를 갖고 있었습니다. 900만 파라미터 모델은 지시를 조건부로 따를 수 없으므로 — 성격은 가중치 안에 새겨져 있습니다. 시스템 프롬프트를 제거하면 추론당 약 60 토큰을 절약합니다.

**왜 싱글턴(단일 턴)만 지원하나요?** 128 토큰 컨텍스트 창 때문에 멀티턴은 3~4번째 턴에서 품질이 무너졌습니다. 잘 잊어버리는 물고기는 콘셉트에 잘 맞지만, 깨진 출력은 아닙니다. 싱글턴이 안정적입니다.

**왜 바닐라 트랜스포머인가요?** GQA, SwiGLU, RoPE, early exit는 900만 파라미터 규모에서는 도움이 되지 않는 복잡성만 더합니다. 표준 어텐션 + ReLU FFN + LayerNorm이 더 단순한 코드로 동일한 품질을 냅니다.

**왜 합성 데이터인가요?** 일관된 성격을 가진 물고기 캐릭터에는 일관된 학습 데이터가 필요합니다. 무작위 구성 요소(수조 사물 30종, 먹이 17종, 활동 25종)를 결합한 템플릿 조합으로 약 60개의 템플릿에서 약 1만 6천 개의 고유한 출력을 생성합니다.

---

## 라이선스

MIT
