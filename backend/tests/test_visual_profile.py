"""The pilot cannot activate through city names, production env or loose flags."""
from itertools import product
from backend.api.visual_profile import selected_profile


def test_visual_rollout_matrix():
    for city, environment, configured in product(
        ['milton-keynes', 'milton-keynes-centre', 'milton-keynes-willen', 'london', ''],
        ['staging', 'production', 'test', 'development', '', 'Staging'],
        ['cinematic-world-v1', '', 'true', 'cinematic-world-v3'],
    ):
        expected = ('cinematic-world-v1' if (city, environment, configured) ==
                    ('milton-keynes', 'staging', 'cinematic-world-v1') else 'standard')
        assert selected_profile(city, environment, configured) == expected


def test_v2_only_installed_approved_staging_cities():
    from backend.api.visual_profile import APPROVED, STYLES
    assert len(STYLES) == 45
    for city in STYLES:
        assert selected_profile(city, "production", "cinematic-world-v2") == "standard"
        assert selected_profile(city, "staging", "cinematic-world-v2") == ("cinematic-world-v2" if city in APPROVED else "standard")
    assert selected_profile("unreviewed-city", "staging", "cinematic-world-v2") == "standard"
