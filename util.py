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
    """Parses the broadcast_iso as UTC and merges with the episode date."""
    try:
        # bangumi-data 'begin' is usually: '2024-01-05T14:30:00.000Z'
        # We take the time part '14:30'
        time_part = "00:00"
        if broadcast_iso and len(broadcast_iso) >= 16:
            time_part = broadcast_iso[11:16]
            
        # Combine with the episode date and mark as UTC (+00:00)
        dt_str = f"{airdate_str} {time_part}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        # Fallback to midnight UTC if something fails
        return datetime.strptime(airdate_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)