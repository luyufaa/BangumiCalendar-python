import hashlib
from datetime import datetime, timedelta
import pytz

def genSummary(name, name_cn, ep):
    title = name_cn if name_cn else name
    return f"{title} {int(ep)}"

def genDec(summary, ep_name):
    return f"Episode Name: {ep_name}\nSummary: {summary}"

def genUUID(sub_id, ep, userid):
    seed = f"{sub_id}-{ep}-{userid}"
    return hashlib.md5(seed.encode()).hexdigest()

def genDateTime(airdate_str, broadcast_iso):
    """Merges Date and ISO Time into a localized Beijing datetime."""
    # Extract HH:MM from ISO (e.g., '14:30')
    time_part = "00:00"
    if broadcast_iso and len(broadcast_iso) >= 16:
        time_part = broadcast_iso[11:16]
    
    # Create object and set to Beijing Time (UTC+8)
    naive_dt = datetime.strptime(f"{airdate_str} {time_part}", "%Y-%m-%d %H:%M")
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return beijing_tz.localize(naive_dt)