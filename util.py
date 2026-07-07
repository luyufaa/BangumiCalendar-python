import hashlib
from datetime import datetime, timedelta, timezone
import pytz # You will need to keep pytz for this method
import json
import os
import re

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

def load_offsets(config_path="offsets.json"):
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
    return {}

def parse_timezone(tz_str):
    if not tz_str:
        return pytz.timezone('Asia/Shanghai')
    
    tz_str = tz_str.strip().upper()
    
    # Check for UTC/GMT offsets: UTC+9, GMT-5, UTC+09:00, etc.
    match = re.match(r'^(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?$', tz_str)
    if match:
        sign, hours, minutes = match.groups()
        minutes = int(minutes) if minutes else 0
        offset_val = int(hours) * 60 + minutes
        if sign == '-':
            offset_val = -offset_val
        return timezone(timedelta(minutes=offset_val))
    
    try:
        return pytz.timezone(tz_str)
    except Exception:
        try:
            return pytz.timezone(tz_str.lower().capitalize())
        except Exception:
            pass
            
    print(f"Warning: Could not parse timezone '{tz_str}'. Defaulting to Asia/Shanghai.")
    return pytz.timezone('Asia/Shanghai')

def localize_dt(dt, tz):
    if hasattr(tz, 'localize'):
        return tz.localize(dt)
    else:
        return dt.replace(tzinfo=tz)

def get_offset_timedelta(subject, offsets):
    key = str(subject.id)
    if key not in offsets:
        return timedelta(0)
    
    val = offsets[key]
    
    # 1. Simple numeric offset (in minutes)
    if isinstance(val, (int, float)):
        return timedelta(minutes=val)
        
    # 2. String offset: check if it specifies a target start time
    target_start_str = ""
    tz_str = ""
    
    if isinstance(val, str):
        # Extract timezone suffix if present like " (UTC+9)" or " UTC+9"
        match = re.search(r'\(([^)]+)\)$', val)
        if match:
            tz_str = match.group(1)
            target_start_str = val[:match.start()].strip()
        else:
            match = re.search(r'\s+((?:UTC|GMT)?[+-]\d+(?::?\d+)?)$', val, re.IGNORECASE)
            if match:
                tz_str = match.group(1)
                target_start_str = val[:match.start()].strip()
            else:
                target_start_str = val
                
    elif isinstance(val, dict):
        if "target_start" in val:
            target_start_str = val["target_start"]
            tz_str = val.get("timezone", "")
        else:
            days = val.get("days", 0)
            hours = val.get("hours", 0)
            minutes = val.get("minutes", 0)
            return timedelta(days=days, hours=hours, minutes=minutes)
            
    # Calculate offset from target start
    if target_start_str:
        try:
            target_dt_naive = datetime.strptime(target_start_str, "%Y-%m-%d %H:%M")
            tz = parse_timezone(tz_str)
            target_dt = localize_dt(target_dt_naive, tz)
            
            standard_iso = subject.broadcast_time
            if not standard_iso:
                print(f"Warning: Subject {subject.id} has no broadcast_time. Cannot calculate target_start offset.")
                return timedelta(0)
            
            standard_date = standard_iso[0:10]
            standard_dt = genDateTime(standard_date, standard_iso)
            
            offset = target_dt - standard_dt
            print(f"Calculated offset for subject {subject.id}: {offset} (standard: {standard_dt}, target: {target_dt})")
            return offset
        except Exception as e:
            print(f"Error calculating offset for subject {subject.id}: {e}")
            
    return timedelta(0)