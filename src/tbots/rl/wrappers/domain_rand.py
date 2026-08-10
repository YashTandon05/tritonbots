"""Inject latency, detection noise, and dropouts.

WITHOUT THIS, SIM-TO-REAL WILL FAIL. rSim hands us perfect instantaneous
state; a real vision frame is 20-40 ms stale, noisy, and sometimes missing
entirely, and our command takes another 10-20 ms to reach the robot. A
policy trained on ground truth learns to rely on information it can never
have at a match.

Randomise the delay, the noise, and the dropout rate per episode rather
than fixing them -- the point is a policy robust across the range, not one
tuned to a particular lab.
"""


from __future__ import annotations

import gymnasium as gym


class DomainRandomization(gym.Wrapper):
    def __init__(self, env, **kwargs) -> None:
        raise NotImplementedError("TASK-054")
