import hashlib
from datetime import datetime, timedelta, timezone, time
import pytz
import json
import os
import re

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

PLATFORM_NAMES = {
    'gamer': '巴哈姆特動畫瘋',
    'gamer_hk': '巴哈姆特香港',
    'netflix': 'Netflix',
    'crunchyroll': 'Crunchyroll',
    'default': 'TV原版'
}

def genSummary(name, name_cn, ep):
    title = name_cn if name_cn else name
    return f"{title} {int(ep)}"

def genDec(summary, ep_name, platform=None):
    desc = f"Episode Name: {ep_name}\nSummary: {summary}"
    if platform and platform in PLATFORM_NAMES:
        desc += f"\nPlatform: {PLATFORM_NAMES[platform]}"
    elif platform and platform != 'default':
        desc += f"\nPlatform: {platform}"
    return desc

def genUUID(sub_id, ep, userid):
    seed = f"{sub_id}-{ep}-{userid}"
    return hashlib.md5(seed.encode()).hexdigest()

def genDateTime(airdate_str, broadcast_iso):
    """
    将 airdate 和 broadcast_iso 组合，转换为 Asia/Shanghai (北京时间) 的 datetime 对象。
    """
    time_part = "00:00"
    if broadcast_iso and len(broadcast_iso) >= 16:
        time_part = broadcast_iso[11:16]

    dt_utc = datetime.strptime(f"{airdate_str} {time_part}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(BEIJING_TZ)

def load_offsets(config_path="offsets.json"):
    """加载番剧自定义偏移配置"""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
    return {}

def save_offsets(offsets, config_path="offsets.json"):
    """保存番剧自定义偏移配置"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(offsets, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {config_path}: {e}")
        return False

def load_config(config_path="config.json"):
    """加载本地配置文件 (包含 USERID、首选平台顺序等)"""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
    return {}

def save_config(config, config_path="config.json"):
    """保存本地配置文件"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {config_path}: {e}")
        return False

def parse_iso(iso_str):
    """将 ISO 时间字符串解析为带时区的 datetime (UTC)"""
    if not iso_str:
        return None
    try:
        clean = re.sub(r'(\.\d+)?Z$', '+00:00', iso_str)
        return datetime.fromisoformat(clean)
    except Exception:
        return None

def parse_timezone(tz_str):
    if not tz_str:
        return BEIJING_TZ

    tz_str = tz_str.strip().upper()

    # UTC/GMT offsets: UTC+8, GMT-5, UTC+08:00
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

    return BEIJING_TZ

def localize_dt(dt, tz):
    if hasattr(tz, 'localize'):
        return tz.localize(dt)
    else:
        return dt.replace(tzinfo=tz)

def set_datetime_time(dt, time_str):
    """设置 datetime 对象的具体时间 (时:分 或 时:分:秒)，保持在北京时间 (Asia/Shanghai)"""
    try:
        parts = [int(p) for p in time_str.strip().split(':')]
        h = parts[0]
        m = parts[1] if len(parts) > 1 else 0
        s = parts[2] if len(parts) > 2 else 0

        dt_local = dt.astimezone(BEIJING_TZ)
        naive_combined = datetime.combine(dt_local.date(), time(h, m, s))
        return BEIJING_TZ.localize(naive_combined)
    except Exception as e:
        print(f"Warning: Failed to set time '{time_str}': {e}")
        return dt

def parse_target_start(target_str, tz_str=""):
    """解析目标首播时间字符串"""
    if not target_str:
        return None

    tz_match = re.search(r'\(([^)]+)\)$', target_str)
    if tz_match:
        tz_str = tz_match.group(1)
        target_str = target_str[:tz_match.start()].strip()
    else:
        tz_match2 = re.search(r'\s+((?:UTC|GMT)?[+-]\d+(?::?\d+)?)$', target_str, re.IGNORECASE)
        if tz_match2:
            tz_str = tz_match2.group(1)
            target_str = target_str[:tz_match2.start()].strip()

    tz = parse_timezone(tz_str)

    # 尝试不同格式解析
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            naive_dt = datetime.strptime(target_str, fmt)
            return localize_dt(naive_dt, tz).astimezone(BEIJING_TZ)
        except ValueError:
            continue
    return None

def get_platform_display_name(platform_key):
    return PLATFORM_NAMES.get(platform_key, platform_key)

def calculate_event_datetime(subject, ep, offsets):
    """
    计算特定剧集 (ep) 的最终日历播出时间 (北京时间 Asia/Shanghai)。
    
    层级处理逻辑：
    1. 平台时间选择：
       - 若 offsets 指定了 platform (如 'gamer', 'netflix', 'crunchyroll', 'tv')，优先采用指定平台；
       - 否则采用 reptile 自动优选的平台 (巴哈姆特 > Netflix > Crunchyroll > TV原版)。
    2. 计算平台基础播出时间：
       - 若所选平台有同步/先行放送时间 (与 TV 时间在 30 天以内)，应用平台的时间及日期差；
       - 若为多年后补买版权，则仅采用平台的每日播出时间，日期保留该季播出日。
    3. 单集先行播放调整 (Episode-level override)：
       - 若 offsets 中指定了该集的单独调整 (如 {"episodes": {"1": {"date": "...", "time": "..."}}} 或 offset_days)，优先直接应用。
    4. 全剧系列级调整 (Series-level adjustment)：
       - target_start: 指定首播完整时间
       - days / offset_days: 整体提前或延后天数 (如先行播放提前 7 天写 -7)
       - time: 强制修改播出时分 (如 "23:30")
       - hours / minutes: 相对微调
    """
    sid = str(subject.id)
    cfg = offsets.get(sid)

    # 1. 确定生效的播出平台与平台时间
    active_platform = getattr(subject, 'platform', 'default')
    active_broadcast = getattr(subject, 'broadcast_time', '')
    default_broadcast = getattr(subject, 'default_broadcast_time', '')
    available_platforms = getattr(subject, 'available_platforms', {})

    if isinstance(cfg, dict) and "platform" in cfg:
        p_req = cfg["platform"].strip().lower()
        if p_req in ("tv", "default", "none"):
            active_platform = "default"
            active_broadcast = default_broadcast
        elif p_req in available_platforms:
            active_platform = p_req
            active_broadcast = available_platforms[p_req]

    # 2. 检查单集先行播放配置 (Episode-specific override)
    ep_num_str = str(ep.ep)
    ep_cfg = None
    if isinstance(cfg, dict) and "episodes" in cfg and isinstance(cfg["episodes"], dict):
        ep_cfg = cfg["episodes"].get(ep_num_str) or cfg["episodes"].get(int(ep.ep) if str(ep.ep).isdigit() else None)

    # 3. 计算平台基础时间 (Base Datetime)
    if active_platform != 'default' and active_broadcast and default_broadcast:
        tv_dt = parse_iso(default_broadcast)
        plat_dt = parse_iso(active_broadcast)
        if tv_dt and plat_dt and abs((plat_dt - tv_dt).days) <= 30:
            # 同步或先行放送 (如提前 7 天、同一天不同时段等)
            delta = plat_dt - tv_dt
            tv_base = genDateTime(ep.airdate, default_broadcast)
            base_dt = tv_base + delta
        else:
            base_dt = genDateTime(ep.airdate, active_broadcast)
    elif active_broadcast:
        base_dt = genDateTime(ep.airdate, active_broadcast)
    else:
        base_dt = genDateTime(ep.airdate, "00:00")

    # 4. 如果有单集先行播放配置，应用单集调整
    if ep_cfg:
        if isinstance(ep_cfg, str):
            # 如 "2026-09-20 20:00"
            parsed_ep_dt = parse_target_start(ep_cfg)
            if parsed_ep_dt:
                return parsed_ep_dt
        elif isinstance(ep_cfg, dict):
            # 指定具体完整日期时间
            if "datetime" in ep_cfg:
                parsed_ep_dt = parse_target_start(ep_cfg["datetime"])
                if parsed_ep_dt:
                    return parsed_ep_dt

            # 指定具体日期和/或时间
            override_date = ep_cfg.get("date")
            override_time = ep_cfg.get("time")
            if override_date and override_time:
                parsed_ep_dt = parse_target_start(f"{override_date} {override_time}")
                if parsed_ep_dt:
                    return parsed_ep_dt
            elif override_date:
                # 仅指定日期，时间沿用 base_dt
                time_str = base_dt.strftime("%H:%M")
                parsed_ep_dt = parse_target_start(f"{override_date} {time_str}")
                if parsed_ep_dt:
                    return parsed_ep_dt
            elif override_time:
                base_dt = set_datetime_time(base_dt, override_time)

            # 单集偏移天数 / 分钟
            ep_days = ep_cfg.get("offset_days") or ep_cfg.get("days", 0)
            if ep_days:
                base_dt = base_dt + timedelta(days=ep_days)

            ep_mins = ep_cfg.get("offset_minutes") or ep_cfg.get("minutes", 0)
            if ep_mins:
                base_dt = base_dt + timedelta(minutes=ep_mins)

            return base_dt

    # 5. 应用系列全剧调整 (Series-level override)
    if cfg is None:
        return base_dt

    # 数值类型：分钟偏移
    if isinstance(cfg, (int, float)):
        return base_dt + timedelta(minutes=cfg)

    # 字符串类型：指定首播时间
    if isinstance(cfg, str):
        target_dt = parse_target_start(cfg)
        if target_dt:
            ref_iso = default_broadcast or active_broadcast
            if ref_iso:
                ref_dt = genDateTime(ref_iso[:10], ref_iso)
                offset = target_dt - ref_dt
                return base_dt + offset
        return base_dt

    # 字典类型配置
    if isinstance(cfg, dict):
        # target_start
        if "target_start" in cfg and cfg["target_start"]:
            target_dt = parse_target_start(cfg["target_start"], cfg.get("timezone", ""))
            if target_dt:
                ref_iso = default_broadcast or active_broadcast
                if ref_iso:
                    ref_dt = genDateTime(ref_iso[:10], ref_iso)
                    offset = target_dt - ref_dt
                    base_dt = base_dt + offset

        # 天数偏移 (用于先行播放提前 X 天，例如 -7)
        days_offset = cfg.get("days") or cfg.get("offset_days", 0)
        if days_offset:
            base_dt = base_dt + timedelta(days=days_offset)

        # 小时/分钟偏移
        hours_offset = cfg.get("hours") or cfg.get("offset_hours", 0)
        minutes_offset = cfg.get("minutes") or cfg.get("offset_minutes", 0)
        if hours_offset or minutes_offset:
            base_dt = base_dt + timedelta(hours=hours_offset, minutes=minutes_offset)

        # 强制指定播出时间 (HH:MM)
        if "time" in cfg and cfg["time"]:
            base_dt = set_datetime_time(base_dt, cfg["time"])

    return base_dt

def get_offset_timedelta(subject, offsets):
    """
    兼容历史代码调用的 offset timedelta 获取函数。
    """
    key = str(subject.id)
    if key not in offsets:
        return timedelta(0)

    val = offsets[key]
    if isinstance(val, (int, float)):
        return timedelta(minutes=val)

    if isinstance(val, str):
        target_dt = parse_target_start(val)
        if target_dt and subject.broadcast_time:
            ref_iso = subject.broadcast_time
            ref_dt = genDateTime(ref_iso[:10], ref_iso)
            return target_dt - ref_dt

    if isinstance(val, dict):
        if "target_start" in val:
            target_dt = parse_target_start(val["target_start"], val.get("timezone", ""))
            if target_dt and subject.broadcast_time:
                ref_iso = subject.broadcast_time
                ref_dt = genDateTime(ref_iso[:10], ref_iso)
                return target_dt - ref_dt
        else:
            days = val.get("days") or val.get("offset_days", 0)
            hours = val.get("hours") or val.get("offset_hours", 0)
            minutes = val.get("minutes") or val.get("offset_minutes", 0)
            return timedelta(days=days, hours=hours, minutes=minutes)

    return timedelta(0)
