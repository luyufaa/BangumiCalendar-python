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
    # USERID is passed from GitHub Secrets
    userid = os.environ.get("USERID")
    
    if not userid:
        print("Error: USERID environment variable is missing. Check GitHub Secrets.")
        exit(1)

    # 1. Fetch data from Bangumi and bangumi-data
    fetcher = data(userid)
    fetcher.getsubjects() # This internal method loads the UTC times
    fetcher.geteps()
    
    # 2. Build the iCalendar
    icl = iCal()
    offsets = util.load_offsets()
    
    for subject in fetcher.subjects:
        offset_td = util.get_offset_timedelta(subject, offsets)

        for ep in fetcher.epdict.get(subject.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                # Generate UTC-aware datetime object
                utc_dt = util.genDateTime(ep.airdate, subject.broadcast_time)
                utc_dt += offset_td
                
                icl.setEvent(
                    summary=util.genSummary(subject.name, subject.name_cn, ep.ep),
                    time=utc_dt,
                    uuid=util.genUUID(subject.id, ep.ep, userid),
                    description=util.genDec(subject.summary, ep.name_cn)
                )

    # 3. Write specifically to target.ics for GitHub Action to commit
    icl.write("target.ics")
    print(f"Successfully generated target.ics for user {userid}")
