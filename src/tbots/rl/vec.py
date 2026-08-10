"""Vectorised environment construction and throughput benchmarking.

rSim is in-process and fast, so throughput is the whole point of training
on it. Build the AsyncVectorEnv here, and benchmark it here too -- every
scaling decision depends on a measured steps/s number, not a guess.
"""


from __future__ import annotations


def make_vec_env(env_fn, n_envs: int, asynchronous: bool = True):
    raise NotImplementedError("TASK-055")


def benchmark(env, n_steps: int = 10_000) -> float:
    """Steps per second. Write the number down; scaling decisions use it."""
    raise NotImplementedError("TASK-055")
