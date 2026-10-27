"""City-local calendars resolve to UTC instants, including DST gaps and folds."""
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from fastapi import HTTPException

COUNTRY_ZONES={'GB':'Europe/London','FR':'Europe/Paris','DE':'Europe/Berlin','NL':'Europe/Amsterdam','ES':'Europe/Madrid','IT':'Europe/Rome','IE':'Europe/Dublin','AE':'Asia/Dubai','SA':'Asia/Riyadh','QA':'Asia/Qatar','IN':'Asia/Kolkata','SG':'Asia/Singapore','JP':'Asia/Tokyo','KR':'Asia/Seoul','TH':'Asia/Bangkok','CN':'Asia/Shanghai'}
CITY_ZONES={'new-york':'America/New_York','miami':'America/New_York','los-angeles':'America/Los_Angeles','toronto':'America/Toronto','vancouver':'America/Vancouver','sydney':'Australia/Sydney','melbourne':'Australia/Melbourne'}

def city_timezone(destination):
 name=(destination.feature_flags or {}).get('timezone') or CITY_ZONES.get(destination.id) or COUNTRY_ZONES.get(destination.country)
 try:return ZoneInfo(name) if name else unavailable()
 except (ZoneInfoNotFoundError,ValueError,TypeError):return unavailable()

def unavailable():raise HTTPException(409,'This destination needs an administrator-configured IANA timezone before booking')

def local_slots(day:date,zone:ZoneInfo):
 seen=set()
 for minute in range(0,1440,30):
  naive=datetime.combine(day,time())+timedelta(minutes=minute)
  for fold in (0,1):
   local=naive.replace(tzinfo=zone,fold=fold);utc=local.astimezone(timezone.utc);stamp=utc.timestamp()
   if utc.astimezone(zone).replace(tzinfo=None)!=naive or stamp in seen:continue
   seen.add(stamp)
   yield {'starts_at':stamp,'label':local.strftime('%H:%M %Z'),'offset':local.strftime('%z')}
