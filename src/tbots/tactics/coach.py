"""The one runtime for tactics, skills, and deterministic safety rules."""

from __future__ import annotations

import math
from dataclasses import replace

from tbots.core.command import RobotCommand, stop
from tbots.core.gamestate import Play
from tbots.core.geometry import FieldGeometry
from tbots.core.state import RobotState, WorldState
from tbots.skills.base import Skill, build_skill
from tbots.tactics.base import SkillSpec, Tactic


class Coach:
    """Run one tactic at a fixed cadence and its skills at control rate.

    ``tick`` is intentionally backend-agnostic.  A simulator or match app
    supplies the world at its control rate and sends the returned commands.
    """

    def __init__(
        self,
        tactic: Tactic,
        geometry: FieldGeometry,
        *,
        decision_hz: float = 4.0,
        control_dt: float = 1.0 / 60.0,
        stop_speed: float = 1.5,
    ) -> None:
        if decision_hz <= 0.0 or control_dt <= 0.0 or stop_speed < 0.0:
            raise ValueError("decision_hz and control_dt must be positive; stop_speed non-negative")
        self.tactic = tactic
        self.geometry = geometry
        self.decision_period = 1.0 / decision_hz
        self.control_dt = control_dt
        # This is explicit because the final rule value remains an open
        # problem.  Match configuration can replace this temporary default.
        self.stop_speed = stop_speed
        self._next_decision: float | None = None
        self._skills: dict[int, tuple[SkillSpec, Skill]] = {}

    def tick(self, world: WorldState) -> list[RobotCommand]:
        """Return one filtered command for every robot in ``world.us``."""
        if self._next_decision is None or world.t + 1e-12 >= self._next_decision:
            self._apply_assignments(world)
            # Advance from the scheduled deadline rather than from ``world.t``
            # to avoid cadence drift when an app presents a late tick.
            if self._next_decision is None:
                self._next_decision = world.t + self.decision_period
            else:
                while self._next_decision <= world.t + 1e-12:
                    self._next_decision += self.decision_period

        commands: list[RobotCommand] = []
        for robot_id in sorted(world.us):
            live = self._skills.get(robot_id)
            if live is None or live[1].status() != "running":
                command = stop(robot_id)
            else:
                command = live[1].step(world, robot_id)
            commands.append(self._filter(world, command))
        return commands

    def _apply_assignments(self, world: WorldState) -> None:
        assignments = self.tactic.decide(world)
        wanted: dict[int, SkillSpec] = {}
        for assignment in assignments:
            if assignment.robot_id not in world.us:
                raise ValueError(f"tactic assigned unknown robot {assignment.robot_id}")
            if assignment.robot_id in wanted:
                raise ValueError(f"tactic assigned robot {assignment.robot_id} twice")
            wanted[assignment.robot_id] = assignment.skill

        for robot_id, spec in wanted.items():
            previous = self._skills.get(robot_id)
            if previous is not None and previous[0] == spec:
                continue
            skill = build_skill(spec.name, **spec.kwargs)
            skill.reset(world, robot_id)
            self._skills[robot_id] = (spec, skill)

        # An omitted robot is intentionally stopped until a future decision.
        for robot_id in set(self._skills) - set(wanted):
            del self._skills[robot_id]

    def _filter(self, world: WorldState, command: RobotCommand) -> RobotCommand:
        game = world.game
        if game.play in (Play.HALT, Play.TIMEOUT) or not game.can_move:
            return stop(command.robot_id)

        candidate = command
        if game.play is Play.STOP:
            candidate = self._limit_speed(candidate, self.stop_speed)

        robot = world.us[command.robot_id]
        next_pos = self._next_pos(robot, candidate)
        if game.min_ball_distance > 0.0 and self._violates_ball_distance(
                robot.pos, next_pos, world.ball.pos, game.min_ball_distance):
            return stop(command.robot_id)

        if (
            command.robot_id != game.our_goalkeeper
            and self.geometry.inside_our_defense_area(*next_pos)
        ):
            return stop(command.robot_id)

        if game.play is not Play.RUN and self._inside_inflated_their_defense_area(next_pos, 0.20):
            return stop(command.robot_id)
        return candidate

    def _next_pos(self, robot: RobotState, command: RobotCommand) -> tuple[float, float]:
        c, s = math.cos(robot.theta), math.sin(robot.theta)
        vx = c * command.vx - s * command.vy
        vy = s * command.vx + c * command.vy
        return (robot.x + vx * self.control_dt, robot.y + vy * self.control_dt)

    @staticmethod
    def _violates_ball_distance(
        current: tuple[float, float],
        candidate: tuple[float, float],
        ball: tuple[float, float],
        minimum: float,
    ) -> bool:
        # A robot already inside the exclusion radius must stop; a controller
        # cannot safely repair that in one tick.  Otherwise reject only motion
        # that would cross the boundary.
        current_distance = math.dist(current, ball)
        return current_distance < minimum or math.dist(candidate, ball) < minimum

    def _inside_inflated_their_defense_area(self, pos: tuple[float, float], margin: float) -> bool:
        # ``FieldGeometry.inside_their_defense_area(..., margin=...)`` has
        # containment semantics, not the outward clearance required here.
        x, y = pos
        return (x >= self.geometry.half_length - self.geometry.penalty_depth - margin
                and abs(y) <= self.geometry.penalty_width / 2.0 + margin)

    @staticmethod
    def _limit_speed(command: RobotCommand, limit: float) -> RobotCommand:
        speed = math.hypot(command.vx, command.vy)
        if speed <= limit or speed == 0.0:
            return command
        scale = limit / speed
        return replace(command, vx=command.vx * scale, vy=command.vy * scale)
