"""GuppyLM configuration."""

from dataclasses import dataclass


@dataclass
class GuppyConfig:
    vocab_size: int = 8192    # bumped from 4096 to fit Korean (3-byte Hangul syllables)
    max_seq_len: int = 128
    d_model: int = 384
    n_layers: int = 6
    n_heads: int = 6
    ffn_hidden: int = 768
    dropout: float = 0.1

    # Mixture-of-Experts (replaces the dense FFN inside every block when use_moe=True)
    use_moe: bool = True      # False -> classic dense FFN (for dense<->MoE comparison)
    n_experts: int = 4        # number of expert FFNs per MoE layer
    moe_top_k: int = 2        # how many experts each token is routed to
    aux_loss_coef: float = 0.01  # weight of the load-balancing auxiliary loss

    # Special tokens
    pad_id: int = 0
    bos_id: int = 1           # <|im_start|>
    eos_id: int = 2           # <|im_end|>


@dataclass
class TrainConfig:
    batch_size: int = 32
    learning_rate: float = 3e-4
    min_lr: float = 3e-5
    weight_decay: float = 0.1
    warmup_steps: int = 200
    max_steps: int = 10000
    eval_interval: int = 200
    save_interval: int = 500
    grad_clip: float = 1.0
    device: str = "auto"
    seed: int = 42
    data_dir: str = "data"
    output_dir: str = "checkpoints"
