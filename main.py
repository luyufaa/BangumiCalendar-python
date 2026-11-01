import util
from iCal import iCal
from reptile import data
import os

'''
Automated update script for GitHub Actions.
Uses environment variable 'USERID' to fetch data.
Writes result to 'target.ics'.
'''

if __name__ == '__main__':
    # USERID is passed from GitHub Secrets, or from config.json when running locally
    userid = os.environ.get("USERID")
    if not userid:
        config = util.load_config()
        userid = config.get("USERID")

    if not userid:
        print("Error: USERID environment variable is missing. Check GitHub Secrets or config.json.")
        exit(1)

    # 1. Fetch data from Bangumi and bangumi-data
    fetcher = data(userid)
    fetcher.getsubjects() # Automatically prioritizes 巴哈姆特 (gamer), Netflix, Crunchyroll
    fetcher.geteps()

    # 2. Build the iCalendar
    icl = iCal()
    offsets = util.load_offsets()

    for subject in fetcher.subjects:
        for ep in fetcher.epdict.get(subject.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                # Generate accurate Beijing datetime considering platform & custom offsets
                event_dt = util.calculate_event_datetime(subject, ep, offsets)

                # Determine active platform for description
                cfg = offsets.get(str(subject.id))
                active_platform = subject.platform
                if isinstance(cfg, dict) and "platform" in cfg:
                    active_platform = cfg["platform"]

                icl.setEvent(
                    summary=util.genSummary(subject.name, subject.name_cn, ep.ep),
                    time=event_dt,
                    uuid=util.genUUID(subject.id, ep.ep, userid),
                    description=util.genDec(subject.summary, ep.name_cn, active_platform)
                )

    # 3. Write specifically to target.ics for GitHub Action to commit
    icl.write("target.ics")
    print(f"Successfully generated target.ics for user {userid}")
