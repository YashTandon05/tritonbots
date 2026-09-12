"""A hand-written, deterministic baseline tactic.

BUILD THIS FIRST. You cannot evaluate a learned tactic without an opponent
to play against, and the scripted baseline is also the yardstick that tells
you whether the learned one is actually better.
"""

from __future__ import annotations

from tbots.core.geometry import FieldGeometry
from tbots.core.state import WorldState
from tbots.tactics.base import Assignment, SkillSpec, Tactic


class ScriptedTactic(Tactic):
    """A predictable opponent for early simulation and evaluation.

    This deliberately does not try to be clever football: the keeper tracks
    the ball on its line, the nearest field robot chases it, and everybody
    else takes a stable support position.  It is useful precisely because it
    is deterministic and needs only ``GoToPoint``.
    """

    def __init__(self, geometry: FieldGeometry) -> None:
        self.geometry = geometry

    def decide(self, world: WorldState) -> list[Assignment]:
        robots = sorted(world.us)
        if not robots:
            return []

        keeper_id = world.game.our_goalkeeper
        if keeper_id not in world.us:
            keeper_id = robots[0]
        field_players = [robot_id for robot_id in robots if robot_id != keeper_id]

        assignments = [
            Assignment(keeper_id, SkillSpec("go_to_point", {
                "target": self._keeper_target(world),
                "face": 0.0,
            }))
        ]
        if not field_players:
            return assignments

        chaser = min(
            field_players,
            key=lambda robot_id: self._distance_sq(world.us[robot_id].pos, world.ball.pos),
        )
        assignments.append(Assignment(chaser, SkillSpec("go_to_point", {
            "target": world.ball.pos,
        })))

        for index, robot_id in enumerate(robot_id for robot_id in field_players
                                         if robot_id != chaser):
            assignments.append(Assignment(robot_id, SkillSpec("go_to_point", {
                "target": self._support_target(world, index),
                "face": 0.0,
            })))
        return assignments

    @staticmethod
    def _distance_sq(a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    def _keeper_target(self, world: WorldState) -> tuple[float, float]:
        # Leave room behind the keeper and do not ask it to leave the goal.
        x = self.geometry.our_goal[0] + 0.30
        y_limit = max(0.0, self.geometry.goal_width / 2.0 - 0.10)
        y = max(-y_limit, min(y_limit, world.ball.y))
        return (x, y)

    def _support_target(self, world: WorldState, index: int) -> tuple[float, float]:
        # Stable lanes behind the ball.  The x position shifts forward only
        # modestly, so the baseline remains a useful defensive opponent.
        lanes = (-1.5, 1.5, -0.75, 0.75, 0.0)
        y = lanes[index % len(lanes)]
        x = max(-2.5, min(1.5, world.ball.x - 1.0 - 0.25 * index))
        return (x, y)
