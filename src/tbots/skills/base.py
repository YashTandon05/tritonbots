"""A Skill is a closed-loop behaviour for ONE robot over MANY control ticks.

The interface is identical whether the implementation is forty lines of
geometry or a neural network. That is what lets someone train a policy on
Tuesday and drop it into the match stack on Wednesday by editing a config.
"""

from __future__ import annotations

from typing import Callable, Literal, Protocol, runtime_checkable

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState

SkillStatus = Literal["running", "success", "failure"]


@runtime_checkable
class Skill(Protocol):
    def reset(self, world: WorldState, robot_id: int) -> None: ...

    def step(self, world: WorldState, robot_id: int) -> RobotCommand: ...

    def status(self) -> SkillStatus: ...


_REGISTRY: dict[str, Callable[..., Skill]] = {}


def register_skill(name: str):
    def deco(cls):
        if name in _REGISTRY:
            raise ValueError(f"skill '{name}' already registered")
        _REGISTRY[name] = cls
        return cls
    return deco


def build_skill(name: str, **kwargs) -> Skill:
    if name not in _REGISTRY:
        raise KeyError(f"unknown skill '{name}'. known: {sorted(_REGISTRY)}")
    return _REGISTRY[name](**kwargs)


def skill_names() -> list[str]:
    return sorted(_REGISTRY)
