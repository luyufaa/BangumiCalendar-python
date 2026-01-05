import hashlib
from datetime import datetime, timedelta, timezone
import pytz # You will need to keep pytz for this method

def genSummary(name, name_cn, ep):
    title = name_cn if name_cn else name
    return f"{title} {int(ep)}"

def genDec(summary, ep_name):
    return f"Episode Name: {ep_name}\nSummary: {summary}"

def genUUID(sub_id, ep, userid):
    seed = f"{sub_id}-{ep}-{userid}"
    return hashlib.md5(seed.encode()).hexdigest()

def genDateTime(airdate_str, broadcast_iso):
    # 1. Parse as UTC (Since bangumi-data is UTC)
    time_part = "00:00"
    if broadcast_iso and len(broadcast_iso) >= 16:
        time_part = broadcast_iso[11:16]
    
    dt_utc = datetime.strptime(f"{airdate_str} {time_part}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    
    # 2. Convert to Beijing Time (Asia/Shanghai)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    dt_beijing = dt_utc.astimezone(beijing_tz)
    
    return dt_beijing