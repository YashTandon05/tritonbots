"""Wrap any trained checkpoint as a Skill.

    skill = LearnedSkill(checkpoint="checkpoints/dribble_v7.pt",
                         obs_builder="egocentric_ball")

Loads a TorchScript module, builds an observation from WorldState via a
named observation builder, runs a forward pass, decodes the output into a
RobotCommand. Must run on CPU in under ~1 ms.

Keep policies small — a few hundred thousand parameters. The virtual
tournament runs team software in a container without root, and a GPU has
to be requested from the technical committee in advance. Assume CPU.
"""

from __future__ import annotations

from tbots.core.command import RobotCommand
from tbots.core.state import WorldState
from tbots.skills.base import Skill, SkillStatus


class LearnedSkill(Skill):
    def __init__(self, checkpoint: str, obs_builder: str) -> None:
        raise NotImplementedError("TASK-037")

    def reset(self, world: WorldState, robot_id: int) -> None:
        raise NotImplementedError("TASK-037")

    def step(self, world: WorldState, robot_id: int) -> RobotCommand:
        raise NotImplementedError("TASK-037")

    def status(self) -> SkillStatus:
        raise NotImplementedError("TASK-037")
