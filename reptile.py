import requests

class Subject:
    def __init__(self, id, name, name_cn, summary, broadcast_time):
        self.id = id
        self.name = name
        self.name_cn = name_cn
        self.summary = summary
        self.broadcast_time = broadcast_time # Captured from bangumi-data

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
        """Fetch broadcast times from bangumi-data project"""
        url = "https://raw.githubusercontent.com/bangumi-data/bangumi-data/master/dist/data.json"
        try:
            res = requests.get(url).json()
            for item in res['items']:
                for site in item.get('sites', []):
                    if site['site'] == 'bangumi':
                        # Store the ISO start time (e.g., 2024-01-01T14:30:00.000Z)
                        self.bgm_data_map[str(site['id'])] = item.get('begin', '')
        except Exception as e:
            print(f"Warning: Could not load bangumi-data: {e}")

    def getsubjects(self):
        self.load_bangumi_data()
        url = f"https://api.bgm.tv/v0/users/{self.userid}/collections?type=3&limit=100"
        res = requests.get(url, headers=self.header).json()
        
        for item in res.get('data', []):
            sub = item['subject']
            sid = str(sub['id'])
            # Match ID to get the broadcast time
            broadcast = self.bgm_data_map.get(sid, "")

            # =======================================================
            # ### INSERT CUSTOM EDITS HERE ###
            # Check for the specific Anime ID (e.g., 364450)
            #if sub['id'] == 364450: 
                # Example 1: Change the translated name
             #   sub['name_cn'] = "Frieren (Custom Name)"
                
                # Example 2: Force a specific broadcast time (ISO format)
                # This overrides the data fetched from bangumi-data
              #  broadcast = "2024-01-05T23:00:00.000Z"

            # Check for another Anime ID
            if sub['id'] == 554013: # 
                broadcast = "2026-01-07T22:00:00.000Z"
            # =======================================================
            
            self.subjects.append(Subject(
                sub['id'], sub['name'], sub['name_cn'], 
                sub.get('short_summary', ''), broadcast
            ))

    def geteps(self):
        for sub in self.subjects:
            url = f"https://api.bgm.tv/v0/episodes?subject_id={sub.id}"
            res = requests.get(url, headers=self.header).json()
            self.epdict[sub.id] = []
            for ep_data in res.get('data', []):
                if ep_data['type'] == 0:
                    self.epdict[sub.id].append(Episode(
                        ep_data['sort'], ep_data['name_cn'], ep_data['airdate']
                    ))
