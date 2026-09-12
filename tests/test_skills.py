import pytest

from tbots.skills import GoToPoint, build_skill, skill_names


def test_builtin_skill_registry_round_trips_go_to_point():
    assert "go_to_point" in skill_names()
    skill = build_skill("go_to_point", target=(1.0, -0.5))
    assert isinstance(skill, GoToPoint)


def test_unknown_skill_has_actionable_error():
    with pytest.raises(KeyError, match="unknown skill"):
        build_skill("does_not_exist")
