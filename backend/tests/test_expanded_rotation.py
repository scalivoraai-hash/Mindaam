import math
from backend.api.locations import CITIES
from backend.api.collectible_rotation import rotation_points,DEFAULTS
from backend.api.world_content import prepared_points,excluded
from backend.api.terrain import permits
from backend.api.geography import traversable

def test_expanded_opportunities_are_bounded_and_safe():
 for city in CITIES:
  name=city['id'];old=prepared_points(name,48);points=rotation_points(name)
  assert len(old)<len(points)<=96,name
  assert points[:len(old)]==old,name
  for x,z in points[len(old):]:
   assert permits(name,x,z) and not excluded(name,x,z) and not traversable(name,x,z,'car'),(name,x,z)
 assert DEFAULTS['density']==16 and DEFAULTS['daily_limit']==96 and DEFAULTS['refresh_minutes']==60
