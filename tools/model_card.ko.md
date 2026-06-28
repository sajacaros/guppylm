---
license: mit
language:
  - en
tags:
  - fish
  - character
  - tiny-llm
  - text-generation
  - from-scratch
pipeline_tag: text-generation
---

<p align="center">
  <img src="assets/guppy.png" alt="GuppyLM" width="300"/>
</p>

<p align="center">
  <a href="https://github.com/arman-bd/guppylm"><img src="https://img.shields.io/badge/GitHub-guppylm-181717?logo=github" alt="GitHub"/></a>&nbsp;
  <a href="https://huggingface.co/datasets/arman-bd/guppylm-60k-generic"><img src="https://img.shields.io/badge/🤗_Dataset-guppylm--60k-blue" alt="Dataset"/></a>&nbsp;
  <a href="https://colab.research.google.com/github/arman-bd/guppylm/blob/main/use_guppylm.ipynb"><img src="https://img.shields.io/badge/Open_in-Colab-F9AB00?logo=googlecolab" alt="Colab"/></a>
  <br/>
  <a href="https://arman-bd.github.io/guppylm/"><img src="https://img.shields.io/badge/Try_in-Browser-64ffda?style=for-the-badge&logo=webassembly&logoColor=white" alt="Browser Demo"/></a>
</p>

# GuppyLM — 900만 파라미터 물고기 챗 모델

작은 물고기 `Guppy`처럼 말하도록 처음부터 학습된 약 900만 파라미터 LLM입니다.

이 프로젝트는 나만의 언어 모델을 학습시키는 것이 마법이 아님을 보여주기 위해 존재합니다. Colab 노트북 하나, 5분이면 처음부터 만든 작동하는 LLM이 완성됩니다.

> 🌐 영어 원본: [model_card.md](model_card.md) · GuppyLM은 영어로만 학습되어 영어로 대화합니다.

## 예시

```
You> hi guppy
Guppy> hi there. i just found a nice spot near the rock. the temperature feels nice.

You> are you hungry
Guppy> yes. always yes. i will swim to the top right now. i promise to eat all of it.

You> what is the meaning of life
Guppy> food. the answer is always food.

You> tell me a joke
Guppy> what did the fish say when it hit the wall. dam.

You> goodnight guppy
Guppy> ok sleep time. i was following a bubble but now i'll stop. goodnight tank. goodnight water.
```

## 아키텍처

| | |
|---|---|
| **파라미터** | 8.7M |
| **종류** | 바닐라 트랜스포머 (처음부터 학습) |
| **레이어** | 6 |
| **히든 차원** | 384 |
| **헤드** | 6 |
| **FFN** | 768 (ReLU) |
| **Vocab** | 2,418 (BPE · 설정 상한 4,096) |
| **최대 시퀀스** | 128 토큰 |
| **정규화** | LayerNorm |
| **위치 인코딩** | 학습형 임베딩 |
| **LM 헤드** | 임베딩과 가중치 공유(weight-tied) |

GQA, RoPE, SwiGLU, early exit는 없습니다. 가능한 한 단순합니다.

## 학습

- **데이터:** 60개 주제에 걸친 6만 건의 싱글턴 합성 대화
- **스텝:** 10,000
- **옵티마이저:** AdamW (코사인 LR 스케줄)
- **하드웨어:** T4 GPU (약 5분)
- **시스템 프롬프트 없음** — 성격이 가중치에 새겨져 있음

## 사용법

```python
from guppylm.inference import GuppyInference

engine = GuppyInference('checkpoints/best_model.pt', 'data/tokenizer.json')
r = engine.chat_completion([{'role': 'user', 'content': 'hi guppy'}])
print(r['choices'][0]['message']['content'])
# hi there. i just found a nice spot near the rock.
```

> **참고:** `inference.py`는 상대 임포트를 사용하므로 패키지 경로(`guppylm.inference`)로 임포트해야 합니다. 저장소 루트에서 실행하세요.

## 링크

- **저장소:** [github.com/arman-bd/guppylm](https://github.com/arman-bd/guppylm)
- **데이터셋:** [huggingface.co/datasets/arman-bd/guppylm-60k-generic](https://huggingface.co/datasets/arman-bd/guppylm-60k-generic)

## 라이선스

MIT
