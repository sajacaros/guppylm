"""
GuppyLM — a tiny fish brain.

Vanilla transformer: multi-head attention, ReLU FFN, LayerNorm, learned positional embeddings.
No GQA, no SwiGLU, no parallel residual, no RoPE. As simple as it gets.

Optionally the dense FFN in every block is replaced by a Mixture-of-Experts (MoE) layer:
a small router picks the top-k of N expert FFNs per token (Switch/Mixtral style), with a
load-balancing auxiliary loss so experts don't collapse onto each other.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from .config import GuppyConfig


class Attention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.n_heads = config.n_heads
        self.head_dim = config.d_model // config.n_heads

        self.qkv = nn.Linear(config.d_model, 3 * config.d_model)
        self.out = nn.Linear(config.d_model, config.d_model)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x, mask=None):
        B, T, C = x.shape
        qkv = self.qkv(x).reshape(B, T, 3, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        attn = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float("-inf"))
        attn = self.dropout(F.softmax(attn, dim=-1))
        return self.out((attn @ v).transpose(1, 2).contiguous().view(B, T, C))


class FFN(nn.Module):
    """Dense feed-forward: one MLP every token goes through."""

    def __init__(self, config):
        super().__init__()
        self.up = nn.Linear(config.d_model, config.ffn_hidden)
        self.down = nn.Linear(config.ffn_hidden, config.d_model)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        return self.dropout(self.down(F.relu(self.up(x))))


class Expert(nn.Module):
    """A single expert — same shape as the dense FFN. There are n_experts of these per MoE layer."""

    def __init__(self, config):
        super().__init__()
        self.up = nn.Linear(config.d_model, config.ffn_hidden)
        self.down = nn.Linear(config.ffn_hidden, config.d_model)

    def forward(self, x):
        return self.down(F.relu(self.up(x)))


class MoEFFN(nn.Module):
    """Mixture-of-Experts feed-forward.

    A router scores all n_experts for each token, keeps the top_k, and returns the
    weighted sum of those experts' outputs — each token's output depends only on its
    top_k experts (the others get gate weight 0).

    Implementation note: experts are applied DENSELY (every expert runs on every token)
    and then masked by the router gate, instead of gathering each expert's assigned
    tokens. The two are mathematically identical, but the dense form has no
    data-dependent control flow (no value-dependent `if`/`nonzero`), so the model
    exports cleanly to ONNX and runs in the browser via onnxruntime-web. Compute here
    grows with n_experts rather than top_k — negligible at this size, and replaceable
    with capacity-based routing at scale.

    Learned routing: experts are NOT assigned roles. The router learns the routing and
    any specialisation (e.g. one expert leaning Korean) emerges during training.

    Also computes a Switch-style load-balancing auxiliary loss and stashes the last
    routing decision (for inspection in eval_routing.py).
    """

    def __init__(self, config):
        super().__init__()
        self.n_experts = config.n_experts
        self.top_k = config.moe_top_k
        self.router = nn.Linear(config.d_model, config.n_experts, bias=False)
        self.experts = nn.ModuleList([Expert(config) for _ in range(config.n_experts)])
        self.dropout = nn.Dropout(config.dropout)

        # Populated each forward — read by training (aux loss) and eval_routing (analysis).
        self.last_aux_loss = None      # scalar tensor, load-balancing penalty
        self.last_topk_idx = None      # (N, top_k) long — which experts each token chose
        self.last_router_probs = None  # (N, n_experts) float — full softmax distribution

    def forward(self, x):
        B, T, C = x.shape
        x_flat = x.reshape(-1, C)                      # (N, C), N = B*T

        router_logits = self.router(x_flat)            # (N, E)
        router_probs = F.softmax(router_logits, dim=-1)

        # Pick the top_k experts per token and renormalise their weights to sum to 1.
        topk_probs, topk_idx = torch.topk(router_probs, self.top_k, dim=-1)  # (N, k)
        topk_probs = topk_probs / (topk_probs.sum(dim=-1, keepdim=True) + 1e-9)

        # Dispatch — dense + masked so the graph has no data-dependent control flow and the
        # model exports to ONNX. Scatter the renormalised top-k weights into a full (N, E) gate
        # (0 for experts a token didn't pick), run every expert on every token, and combine by
        # the gate. Non-routed experts contribute 0, so the result is identical to gathering only
        # each expert's assigned tokens — only the (wasted) compute differs.
        gate = torch.zeros_like(router_probs).scatter(1, topk_idx, topk_probs)  # (N, E)
        out = torch.zeros_like(x_flat)
        for e in range(self.n_experts):
            out = out + gate[:, e:e + 1] * self.experts[e](x_flat)
        out = self.dropout(out).reshape(B, T, C)

        # ── Switch load-balancing aux loss ──────────────────────────────────
        # P_i = mean router prob to expert i; f_i = fraction of dispatch slots to expert i.
        # aux = E * Σ f_i·P_i  (minimised, == 1, when load is uniform).
        N = x_flat.shape[0]
        P = router_probs.mean(dim=0)                                  # (E,)
        one_hot = F.one_hot(topk_idx, self.n_experts).float()        # (N, k, E)
        f = one_hot.sum(dim=(0, 1)) / (N * self.top_k)               # (E,), sums to 1
        self.last_aux_loss = self.n_experts * torch.sum(f * P)

        self.last_topk_idx = topk_idx.detach()
        self.last_router_probs = router_probs.detach()
        return out


class Block(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.norm1 = nn.LayerNorm(config.d_model)
        self.attn = Attention(config)
        self.norm2 = nn.LayerNorm(config.d_model)
        self.ffn = MoEFFN(config) if config.use_moe else FFN(config)

    def forward(self, x, mask=None):
        x = x + self.attn(self.norm1(x), mask)
        x = x + self.ffn(self.norm2(x))
        return x


class GuppyLM(nn.Module):
    def __init__(self, config: GuppyConfig):
        super().__init__()
        self.config = config

        self.tok_emb = nn.Embedding(config.vocab_size, config.d_model)
        self.pos_emb = nn.Embedding(config.max_seq_len, config.d_model)
        self.drop = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList([Block(config) for _ in range(config.n_layers)])
        self.norm = nn.LayerNorm(config.d_model)
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.lm_head.weight = self.tok_emb.weight  # tie weights

        self.apply(self._init_weights)

        # Last-step loss breakdown (filled in forward, read by the training loop for logging).
        self.last_ce_loss = None
        self.last_aux_loss = None

    @property
    def moe_layers(self):
        """All MoE feed-forward layers (empty when use_moe=False)."""
        return [m for m in self.modules() if isinstance(m, MoEFFN)]

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        pos = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        mask = torch.tril(torch.ones(T, T, device=idx.device)).unsqueeze(0).unsqueeze(0)

        for block in self.blocks:
            x = block(x, mask)

        logits = self.lm_head(self.norm(x))

        loss = None
        if targets is not None:
            ce_loss = F.cross_entropy(
                logits.view(-1, self.config.vocab_size),
                targets.view(-1),
                ignore_index=0,
            )
            # Sum the load-balancing penalty across every MoE layer (0 when dense).
            moe = self.moe_layers
            if moe:
                aux_loss = torch.stack([m.last_aux_loss for m in moe]).mean()
            else:
                aux_loss = torch.zeros((), device=logits.device)
            self.last_ce_loss = ce_loss.detach()
            self.last_aux_loss = aux_loss.detach()
            loss = ce_loss + self.config.aux_loss_coef * aux_loss

        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens=64, temperature=0.7, top_k=50, **kwargs):
        self.eval()
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.config.max_seq_len:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float("-inf")
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
            if next_id.item() == self.config.eos_id:
                break
        return idx, []

    def param_count(self):
        """Returns (total, active) param counts.

        `active` is the params a single token actually flows through: with top-k MoE the
        experts it doesn't pick don't run, so they don't count toward per-token compute.
        For a dense model active == total.
        """
        total = sum(p.numel() for p in self.parameters())
        inactive = 0
        for m in self.moe_layers:
            per_expert = sum(p.numel() for p in m.experts[0].parameters())
            inactive += per_expert * (m.n_experts - m.top_k)
        active = total - inactive
        return total, active

    def param_summary(self):
        total, active = self.param_count()
        if self.config.use_moe:
            return (f"GuppyLM (MoE {self.config.n_experts}x top-{self.config.moe_top_k}): "
                    f"{total/1e6:.1f}M total / {active/1e6:.1f}M active per token")
        return f"GuppyLM (dense): {total:,} params ({total/1e6:.1f}M)"
