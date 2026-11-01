import requests
import re
from datetime import datetime

# 优先使用的流媒体平台列表（按优先级排序）
# 1. 巴哈姆特動畫瘋 (gamer / gamer_hk)
# 2. Netflix (netflix)
# 3. Crunchyroll (crunchyroll)
PREFERRED_PLATFORMS = ['gamer', 'gamer_hk', 'netflix', 'crunchyroll']

PLATFORM_NAMES = {
    'gamer': '巴哈姆特動畫瘋',
    'gamer_hk': '巴哈姆特香港',
    'netflix': 'Netflix',
    'crunchyroll': 'Crunchyroll',
    'default': 'TV原版'
}

def extract_timestamp(site_obj):
    """从 site 对象中提取有效的 ISO 时间字符串"""
    if not site_obj:
        return ""
    begin = site_obj.get('begin')
    if begin:
        return begin
    broadcast = site_obj.get('broadcast')
    if broadcast:
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)', broadcast)
        if m:
            return m.group(1)
    return ""

def parse_iso(iso_str):
    """将 ISO 时间字符串解析为带时区的 datetime 对象 (UTC)"""
    if not iso_str:
        return None
    try:
        clean = re.sub(r'(\.\d+)?Z$', '+00:00', iso_str)
        return datetime.fromisoformat(clean)
    except Exception:
        return None

class Subject:
    def __init__(self, id, name, name_cn, summary, broadcast_time,
                 default_broadcast_time="", platform="default", available_platforms=None):
        self.id = id
        self.name = name
        self.name_cn = name_cn
        self.summary = summary
        self.broadcast_time = broadcast_time                 # 生效的播放时间 (ISO 字符串)
        self.default_broadcast_time = default_broadcast_time # TV 默认播放时间 (ISO 字符串)
        self.platform = platform                             # 生效的平台标识 (如 gamer, netflix, crunchyroll, default)
        self.available_platforms = available_platforms or {} # 所有可用平台时间 {'gamer': '...', 'netflix': '...'}

class Episode:
    def __init__(self, ep, name_cn, airdate):
        self.ep = ep
        self.name_cn = name_cn
        self.airdate = airdate

class data:
    def __init__(self, userid):
        self.userid = userid
        self.subjects = []
        self.epdict = {}
        self.header = {'User-Agent': 'Mozilla/5.0'}
        self.bgm_data_map = {}

    def load_bangumi_data(self):
        """
        从 bangumi-data 项目获取番剧播放时间。
        优先检查并使用 巴哈姆特 (gamer/gamer_hk)、Netflix (netflix)、Crunchyroll (crunchyroll) 的播放时间。
        """
        url = "https://raw.githubusercontent.com/bangumi-data/bangumi-data/master/dist/data.json"
        try:
            res = requests.get(url).json()
            for item in res['items']:
                # 寻找对应的 Bangumi Subject ID
                bgm_id = None
                for site in item.get('sites', []):
                    if site.get('site') == 'bangumi':
                        bgm_id = str(site.get('id'))
                        break
                if not bgm_id:
                    continue

                item_begin = item.get('begin', '')
                item_dt = parse_iso(item_begin)

                # 收集所有平台的播出时间
                available = {}
                for site in item.get('sites', []):
                    s_name = site.get('site')
                    ts = extract_timestamp(site)
                    if ts:
                        available[s_name] = ts

                # 按优先级选择流媒体平台时间
                chosen_platform = 'default'
                chosen_time = item_begin

                for p in PREFERRED_PLATFORMS:
                    if p in available:
                        p_ts = available[p]
                        p_dt = parse_iso(p_ts)
                        if p_dt:
                            # 校验是否为同步/先行播出（与 TV 放送时间在 30 天以内，避免把多年后补买版权的流媒体上传时间当成新番放送）
                            if item_dt is None or abs((p_dt - item_dt).days) <= 30:
                                chosen_platform = p
                                chosen_time = p_ts
                                break

                # 如果没有符合条件的流媒体，且 TV 原版时间不存在，但流媒体有时间，则降级选用
                if chosen_platform == 'default' and not chosen_time:
                    for p in PREFERRED_PLATFORMS:
                        if p in available:
                            chosen_platform = p
                            chosen_time = available[p]
                            break

                self.bgm_data_map[bgm_id] = {
                    'broadcast_time': chosen_time,
                    'default_broadcast_time': item_begin,
                    'platform': chosen_platform,
                    'available_platforms': available
                }
        except Exception as e:
            print(f"Warning: Could not load bangumi-data: {e}")

    def getsubjects(self):
        self.load_bangumi_data()
        limit = 100
        offset = 0
        total = None

        while total is None or offset < total:
            url = f"https://api.bgm.tv/v0/users/{self.userid}/collections?type=3&limit={limit}&offset={offset}"
            try:
                res = requests.get(url, headers=self.header).json()
            except Exception as e:
                print(f"Error fetching collections: {e}")
                break

            total = res.get('total', 0)
            items = res.get('data', [])
            if not items:
                break

            for item in items:
                sub = item['subject']
                sid = str(sub['id'])

                meta = self.bgm_data_map.get(sid, {})
                broadcast = meta.get('broadcast_time', '')
                default_broadcast = meta.get('default_broadcast_time', '')
                platform = meta.get('platform', 'default')
                available = meta.get('available_platforms', {})

                self.subjects.append(Subject(
                    sub['id'],
                    sub['name'],
                    sub.get('name_cn') or sub['name'],
                    sub.get('short_summary', ''),
                    broadcast,
                    default_broadcast_time=default_broadcast,
                    platform=platform,
                    available_platforms=available
                ))

            offset += len(items)

    def geteps(self):
        for sub in self.subjects:
            url = f"https://api.bgm.tv/v0/episodes?subject_id={sub.id}"
            try:
                res = requests.get(url, headers=self.header).json()
            except Exception as e:
                print(f"Error fetching episodes for subject {sub.id}: {e}")
                continue

            self.epdict[sub.id] = []
            for ep_data in res.get('data', []):
                if ep_data.get('type') == 0:
                    self.epdict[sub.id].append(Episode(
                        ep_data['sort'], ep_data.get('name_cn', ''), ep_data.get('airdate', '')
                    ))
