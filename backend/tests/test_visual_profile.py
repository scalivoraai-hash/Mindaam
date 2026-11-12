"""Approved cities require the exact rollout flag in an eligible environment."""
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


def test_v2_only_installed_approved_cities_and_environments():
    from backend.api.visual_profile import APPROVED, STYLES
    assert len(STYLES) == 45
    for city in STYLES:
        for environment in ('staging','production'):
            assert selected_profile(city, environment, "cinematic-world-v2") == ("cinematic-world-v2" if city in APPROVED else "standard")
        for environment in ('test','development','','Production'):
            assert selected_profile(city, environment, "cinematic-world-v2") == "standard"
    assert selected_profile("unreviewed-city", "staging", "cinematic-world-v2") == "standard"

def test_geography_carries_the_current_authoritative_rollout(monkeypatch):
    from backend.api.geography import geometry
    # Initialise endpoint dependencies under the test database environment;
    # only the runtime presentation decision varies below.
    from backend.api import grand_arena
    import json
    for environment,flag,expected in [('staging','cinematic-world-v2','cinematic-world-v2'),
                                     ('production','cinematic-world-v2','cinematic-world-v2'),
                                     ('production','','standard')]:
        monkeypatch.setenv('APP_ENV',environment)
        monkeypatch.setenv('MINDAAM_VISUAL_PROFILE',flag)
        assert json.loads(geometry('london').body)['visual_profile']==expected
