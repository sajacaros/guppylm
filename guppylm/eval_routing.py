"""MoE routing analysis — watch which experts Korean vs English tokens flow to.

The headline question for a learned-routing MoE: did the experts specialise? After training,
this runs Korean and English prompts through one forward pass each, tallies how often each
expert is picked (across every MoE layer), and prints the per-language distribution. If a
couple of experts lean Korean and others lean English, you can see it here.

    python -m guppylm route
"""

import argparse

import torch

from .inference import GuppyInference


KO_PROMPTS = [
    "안녕 구피", "배고프니", "오늘 너무 더워", "물 갈아줬어", "잘 자 구피",
    "거품 좋아해?", "삶의 의미가 뭐야", "고양이가 너 보고 있어", "사랑해 구피", "농담 하나 해줘",
]
EN_PROMPTS = [
    "hi guppy", "are you hungry", "it's really hot today", "i changed your water",
    "goodnight guppy", "do you like bubbles", "what is the meaning of life",
    "the cat is watching you", "i love you guppy", "tell me a joke",
]


def _encode_prompt(tokenizer, prompt):
    text = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    return tokenizer.encode(text).ids


@torch.no_grad()
def route_counts(model, tokenizer, prompts, device):
    """One forward pass per prompt; tally expert picks across all MoE layers."""
    n_experts = model.config.n_experts
    counts = torch.zeros(n_experts)
    for p in prompts:
        ids = _encode_prompt(tokenizer, p)
        x = torch.tensor([ids], dtype=torch.long, device=device)
        model(x)  # no targets — just populates each MoEFFN.last_topk_idx
        for m in model.moe_layers:
            idx = m.last_topk_idx.reshape(-1).cpu()  # every (token, slot) expert pick
            counts += torch.bincount(idx, minlength=n_experts).float()
    return counts


def _bar(frac, width=24):
    filled = int(round(frac * width))
    return "█" * filled + "·" * (width - filled)


def analyze(checkpoint, tokenizer_path, device="cpu"):
    engine = GuppyInference(checkpoint, tokenizer_path, device)
    model = engine.model

    if not model.config.use_moe:
        print("Model is dense (use_moe=False) — no experts to route. Nothing to analyze.")
        return

    n_experts = model.config.n_experts
    print(f"\nMoE routing analysis — {n_experts} experts, top-{model.config.moe_top_k}, "
          f"{len(model.moe_layers)} MoE layers")
    print("Share of expert selections per language (summed over all layers & tokens):\n")

    dist = {}
    for lang, prompts in [("Korean", KO_PROMPTS), ("English", EN_PROMPTS)]:
        counts = route_counts(model, engine.tokenizer, prompts, engine.device)
        total = counts.sum().item()
        dist[lang] = [counts[e].item() / max(total, 1) for e in range(n_experts)]
        print(f"[{lang}]  ({len(prompts)} prompts)")
        for e in range(n_experts):
            frac = dist[lang][e]
            print(f"  expert {e}: {_bar(frac)} {frac*100:5.1f}%  ({int(counts[e])})")
        print()

    # Which experts each language leans on more than the other — the specialisation signal.
    print("Language lean per expert (Korean share − English share):")
    for e in range(n_experts):
        diff = dist["Korean"][e] - dist["English"][e]
        lean = "→ Korean" if diff > 0.03 else ("→ English" if diff < -0.03 else "  (shared)")
        print(f"  expert {e}: {diff*100:+5.1f} pts  {lean}")

    print("\nSample responses (both languages should work):")
    for p in ["안녕 구피", "배고프니", "hi guppy", "are you hungry"]:
        r = engine.chat_completion([{"role": "user", "content": p}])["choices"][0]["message"]["content"]
        print(f"  {p!r:22} -> {r}")


def main():
    ap = argparse.ArgumentParser(description="Analyze MoE expert routing by language")
    ap.add_argument("--checkpoint", default="checkpoints/best_model.pt")
    ap.add_argument("--tokenizer", default="data/tokenizer.json")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    analyze(args.checkpoint, args.tokenizer, args.device)


if __name__ == "__main__":
    main()
