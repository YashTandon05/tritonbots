"""Hydra entry point.

    python -m tbots.rl.train reward=... env=...

The command recruits will run on day one, so it has to compose the configs
from configs/ (env, reward, curriculum) and nothing else. Changing a reward
means editing YAML, never editing an environment.
"""


from __future__ import annotations


def main() -> None:
    raise NotImplementedError("TASK-056")


if __name__ == "__main__":
    main()
