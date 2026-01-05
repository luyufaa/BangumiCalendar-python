import hashlib
from datetime import datetime, timezone

def genSummary(name, name_cn, ep):
    title = name_cn if name_cn else name
    return f"{title} {int(ep)}"

def genDec(summary, ep_name):
    return f"Episode Name: {ep_name}\nSummary: {summary}"

def genUUID(sub_id, ep, userid):
    seed = f"{sub_id}-{ep}-{userid}"
    return hashlib.md5(seed.encode()).hexdigest()

def genDateTime(airdate_str, broadcast_iso):
    # Extract HH:MM (e.g., 14:00)
    time_part = "00:00"
    if broadcast_iso and len(broadcast_iso) >= 16:
        time_part = broadcast_iso[11:16]
    
    dt_str = f"{airdate_str} {time_part}"
    # replace(tzinfo=timezone.utc) is CRITICAL here
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)