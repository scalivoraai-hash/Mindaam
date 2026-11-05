import pytest
from pydantic import ValidationError
from backend.api.core import Onboarding
from backend.api.avatar_schema import CATALOG, validate_avatar

def test_legacy_values_are_preserved():
    value={'color':'#50ddab','style':'cap','skin':'#b98462','hair':'#301d17','pants':'#174158'}
    assert validate_avatar(value)==value
    assert validate_avatar({})=={}

@pytest.mark.parametrize('value',[
 {'asset':'https://example.com/evil.glb'}, {'style':'../../asset'}, {'figure':'super-cool'},
 {'color':'url(javascript:bad)'}, {'version':'3'}, {'carry':['camera']}, {'style':'x'*3000},
])
def test_invalid_cosmetics_rejected(value):
    with pytest.raises(ValidationError): Onboarding(city='london',avatar=value)

def test_every_catalogue_option_is_allowlisted_without_gender_or_city_restrictions():
    for key,options in CATALOG.items():
        if key=='presets':continue
        for option in options:
            assert validate_avatar({'version':'2',key:option})[key]==option

def test_payload_is_copied():
    original={'version':'2','style':'mullappoo','bottom':'mundu'}
    result=validate_avatar(original);result['style']='short'
    assert original['style']=='mullappoo'
