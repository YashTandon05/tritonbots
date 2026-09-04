"""Hydra entry point.

    python -m tbots.rl.train reward=... env=...

The command recruits will run on day one, so it has to compose the configs
from configs/ (env, reward, curriculum) and nothing else. Changing a reward
means editing YAML, never editing an environment.
"""


from __future__ import annotations

from pathlib import Path

import hydra
from omegaconf import DictConfig

from tbots.rl.artifacts import write_resolved_config


def prepare_run(cfg: DictConfig) -> Path:
    """Validate and record a requested run before a trainer consumes it."""
    run_dir = Path(cfg.train.run_dir)
    if not str(run_dir):
        raise ValueError("train.run_dir must not be empty")
    write_resolved_config(run_dir, cfg)
    return run_dir


@hydra.main(version_base="1.3", config_path="../../../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    prepare_run(cfg)
    raise NotImplementedError(
        "No PPO or other RL algorithm exists in this repository. "
        "TASK-056 currently provides config composition and run artifacts only; "
        "add a chosen trainer before invoking it for training."
    )


if __name__ == "__main__":
    main()
