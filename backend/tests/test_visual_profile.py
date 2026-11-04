"""The pilot cannot activate through city names, production env or loose flags."""
from itertools import product
from backend.api.visual_profile import selected_profile


def test_visual_rollout_matrix():
    for city, environment, configured in product(
        ['milton-keynes', 'milton-keynes-centre', 'milton-keynes-willen', 'london', ''],
        ['staging', 'production', 'test', 'development', '', 'Staging'],
        ['cinematic-world-v1', '', 'true', 'cinematic-world-v2'],
    ):
        expected = ('cinematic-world-v1' if (city, environment, configured) ==
                    ('milton-keynes', 'staging', 'cinematic-world-v1') else 'standard')
        assert selected_profile(city, environment, configured) == expected
