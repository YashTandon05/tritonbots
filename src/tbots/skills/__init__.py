"""Built-in skills available through :func:`build_skill`.

Keep this list deliberate.  Importing the package is the registration point,
but it must not pull in optional ML dependencies or unfinished skills.
"""

from tbots.skills.base import Skill, SkillStatus, build_skill, register_skill, skill_names
from tbots.skills.go_to_point import GoToPoint

__all__ = [
    "GoToPoint",
    "Skill",
    "SkillStatus",
    "build_skill",
    "register_skill",
    "skill_names",
]
