from panini.async_test_client import is_subject_matches_pattern


def test_is_subject_matches_pattern():
    assert is_subject_matches_pattern("asdf.>", "asdf.>") is True
    assert is_subject_matches_pattern("asdf.>.1234.*", "asdf.>") is True
    assert is_subject_matches_pattern("asdf.>.1234.*", "asdf.*") is False
    assert is_subject_matches_pattern("asdf.*.*.*", "asdf.*") is False
    assert is_subject_matches_pattern("asdf.*.*.*", "asdf.*.*.*") is True
    assert is_subject_matches_pattern("asdf.*.asdf.*", "asdf.*.*.*") is True
    assert is_subject_matches_pattern("asdf.*.*.*", "asdf.*.asdf.*") is False
    assert (
        is_subject_matches_pattern("asdf.asdf.asdf.asdf", "asdf.asdf.asdf.asdf") is True
    )
