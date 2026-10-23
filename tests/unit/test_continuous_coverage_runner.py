import pytest
from scripts.run_continuous_coverage_training import nearest_rank


def test_nearest_rank_uses_upper_observation_for_six_sample_p95() -> None:
    assert nearest_rank([3.4, 3.7, 3.73, 3.83, 4.12, 5.63], 0.95) == 5.63
    assert nearest_rank([3.4, 3.7, 3.73, 3.83, 4.12, 5.63], 0.50) == 3.73


def test_nearest_rank_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="no values"):
        nearest_rank([], 0.95)
