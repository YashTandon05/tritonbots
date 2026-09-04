from __future__ import annotations

import pytest
from omegaconf import OmegaConf

from tbots.rl.artifacts import load_checkpoint, save_checkpoint, write_resolved_config


def test_resolved_config_records_overrides(tmp_path):
    config = OmegaConf.create({"train": {"run_dir": "runs/example", "num_envs": 8}})

    path = write_resolved_config(tmp_path, config)

    assert OmegaConf.load(path).train.num_envs == 8


def test_checkpoint_round_trip_and_metadata_validation(tmp_path):
    pytest.importorskip("torch")
    path = save_checkpoint(tmp_path, {"metadata": {"observation": "skill-v1"}, "step": 42})

    assert load_checkpoint(path, expected_metadata={"observation": "skill-v1"})["step"] == 42
    with pytest.raises(ValueError, match="metadata"):
        load_checkpoint(path, expected_metadata={"observation": "other"})
