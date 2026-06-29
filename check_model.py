from guppylm.config import GuppyConfig
from guppylm.model import GuppyLM

for moe in (False, True):
    m = GuppyLM(GuppyConfig(use_moe=moe))
    print(m.param_summary())
