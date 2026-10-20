"""Turn the existing ornament car positions into stable rental/scenery identities."""
import math
from functools import lru_cache
from .geography import district,traversable

@lru_cache(maxsize=64)
def placements(city):
    geo=district(city);ornament=0;out=[]
    roads=sorted((f for f in geo['features'] if f['tags'].get('highway') and len(f['points'])>1),key=lambda f:math.dist(f['points'][0],geo['spawn']))
    for f in roads:
        for a,b in zip(f['points'],f['points'][1:]):
            length=math.dist(a,b)
            if length<12:continue
            nx,nz=(b[1]-a[1])/length,-(b[0]-a[0])/length
            for k in range(8,math.ceil(length),28):
                if k>=length:continue
                x,z=a[0]+(b[0]-a[0])*k/length+nx*8,a[1]+(b[1]-a[1])*k/length+nz*8
                if math.hypot(x,z)>480:continue
                ornament+=1
                if ornament>201:continue
                if ornament%7:continue
                cx,cz=x-nx*10,z-nz*10
                public=f['tags'].get('access') not in ['private','no']
                valid=public and traversable(city,cx,cz,'car')
                out.append({'id':f'{city}:street:{ornament}','kind':'car','x':cx,'z':cz,'heading':math.atan2(b[0]-a[0],b[1]-a[1]),'classification':'RENTABLE' if valid else 'SCENERY_ONLY'})
                bx,bz=x-nx*3.2,z-nz*3.2
                if public and ornament%14==0 and traversable(city,bx,bz) and not traversable(city,bx,bz,'car'):
                    out.append({'id':f'{city}:street-bike:{ornament}','kind':'bike','x':bx,'z':bz,'heading':math.atan2(b[0]-a[0],b[1]-a[1]),'classification':'RENTABLE'})
    return out
