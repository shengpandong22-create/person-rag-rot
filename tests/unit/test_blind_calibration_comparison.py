from scripts.compare_blind_calibration import compare


def test_compare_counts_quality_and_review_agreement_separately() -> None:
    left = {
        "blind-01": {"quality": "好", "needs_review": False},
        "blind-02": {"quality": "一般", "needs_review": True},
    }
    right = {
        "blind-01": {"quality": "好", "needs_review": True},
        "blind-02": {"quality": "差", "needs_review": True},
    }

    report = compare(left, right)

    assert report["quality_agreement_count"] == 1
    assert report["review_agreement_count"] == 1
    assert report["exact_pair_agreement_count"] == 0
