from dccp.cardivex_bridge import ordinal_axis_distance, ordinal_vector_euclidean


def test_ordinal_axis_distance_matches_legacy_mean_absolute_levels():
    a = {"a": "none", "b": "moderate", "c": "high"}
    b = {"a": "severe", "b": "low", "c": "substantial"}
    expected = (5 + 1 + 1) / 3
    assert abs(ordinal_axis_distance(a, b) - expected) < 1e-12


def test_ordinal_vector_euclidean_matches_raw_euclidean():
    a = [0.0, 2.0, 4.0]
    b = [5.0, 1.0, 3.0]
    expected = ((5.0**2) + (1.0**2) + (1.0**2)) ** 0.5
    assert abs(ordinal_vector_euclidean(a, b) - expected) < 1e-12
