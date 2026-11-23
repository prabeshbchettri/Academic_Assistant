import pytest

from configs.schema import load_category_config, preload_all_configs


def test_load_all_category_configs():
    configs = preload_all_configs()
    assert "assignment" in configs
    assert "initial_lab" in configs
    assert "final_lab" in configs

    for name, cfg in configs.items():
        assert cfg.category == name
        assert len(cfg.required_sections) > 0
        assert cfg.word_limits.total.min > 0
        assert cfg.word_limits.total.max >= cfg.word_limits.total.min

        # Verify rubric weights sum to 1.0
        total_weight = sum(item.weight for item in cfg.rubric)
        assert pytest.approx(total_weight, 1e-4) == 1.0


def test_assignment_config_details():
    cfg = load_category_config("assignment")
    assert "introduction" in cfg.required_sections
    assert "conclusion" in cfg.required_sections
    assert cfg.word_limits.sections["introduction"].min == 100
