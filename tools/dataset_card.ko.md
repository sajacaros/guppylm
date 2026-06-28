---
license: mit
task_categories:
  - text-generation
language:
  - en
size_categories:
  - 10K<n<100K
tags:
  - fish
  - character
  - tiny-llm
  - synthetic
pretty_name: GuppyLM Chat
---

<p align="center">
  <img src="assets/guppy.png" alt="GuppyLM" width="300"/>
</p>

<p align="center">
  <a href="https://github.com/arman-bd/guppylm"><img src="https://img.shields.io/badge/GitHub-guppylm-181717?logo=github" alt="GitHub"/></a>&nbsp;
  <a href="https://huggingface.co/arman-bd/guppylm-9M"><img src="https://img.shields.io/badge/🤗_Model-guppylm--9M-orange" alt="Model"/></a>&nbsp;
  <a href="https://colab.research.google.com/github/arman-bd/guppylm/blob/main/train_guppylm.ipynb"><img src="https://img.shields.io/badge/Open_in-Colab-F9AB00?logo=googlecolab" alt="Colab"/></a>
  <br/>
  <a href="https://arman-bd.github.io/guppylm/"><img src="https://img.shields.io/badge/Try_in-Browser-64ffda?style=for-the-badge&logo=webassembly&logoColor=white" alt="Browser Demo"/></a>
</p>

# GuppyLM 챗 데이터셋

GuppyLM 학습용 데이터 — 작은 물고기처럼 말하는 약 900만 파라미터 LLM을 위한 것입니다.

> 🌐 영어 원본: [dataset_card.md](dataset_card.md) · 데이터는 영어로 작성되어 있습니다.

## 데이터셋 설명

인간과 작은 물고기 캐릭터 Guppy 사이의 6만 건 싱글턴 대화입니다.
Guppy는 물, 먹이, 빛, 수조 생활에 대해 짧고 소문자로 된 문장으로 말합니다.
인간의 추상적 개념은 이해하지 못합니다.

### 예시

```
Input:  are you hungry
Output: yes. always yes. i will swim to the top right now.

Input:  what do you think about politics
Output: i don't know what politics is. is it wet.

Input:  goodnight guppy
Output: night. i'll rest near the bottom. maybe tomorrow there will be pellets.
```

## 필드

| 필드 | 타입 | 설명 |
|-------|------|-------------|
| `input` | string | 사용자 메시지 |
| `output` | string | Guppy의 응답 |
| `category` | string | 주제 카테고리 (60개) |

## 카테고리

`category` 필드의 실제 값(60개)은 다음과 같습니다:

```
greeting, feeling, temp_hot, temp_cold, food, light, water, about, confused,
tank, noise, night, lonely, misc, bye, bubbles, glass, reflection, breathing,
swimming, colors, taste, plants, filter, algae, snail, glass_tap, scared,
excited, bored, curious, happy, tired, outside, cat, rain, seasons, music,
visitors, children, meaning, time, memory, dreams, size, future, past, name,
weather, sleep, friends, joke, fear, love, age, smart, poop, doctor, singing, tv
```

> **참고:** 카테고리 키는 위 문자열을 그대로 사용합니다. 예를 들어 "지능"은 `smart`, "화장실"은 `poop`, "건강"은 `doctor` 키에 대응합니다. 필터링할 때는 키 문자열을 기준으로 하세요.

## 사용법

```python
from datasets import load_dataset
ds = load_dataset("arman-bd/guppylm-60k-generic")
print(ds["train"][0])
# {'input': 'hi guppy', 'output': 'hello. the water is nice today.', 'category': 'greeting'}
```

## 생성 방식

데이터는 무작위 구성 요소(수조 사물, 먹이 종류, 활동, 신체 부위 등)를 결합한 템플릿 조합으로 합성 생성되며, 이를 통해 높은 출력 다양성을 확보합니다.

## 링크

- **저장소:** [github.com/arman-bd/guppylm](https://github.com/arman-bd/guppylm)
- **모델:** [huggingface.co/arman-bd/guppylm-9M](https://huggingface.co/arman-bd/guppylm-9M)

## 라이선스

MIT
