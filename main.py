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
    
    for subject in fetcher.subjects:
        # Get UTC time for the title label
        # format: "2024-01-05T14:30:00.000Z" -> "14:30"
        utc_label = subject.broadcast_time[11:16] if subject.broadcast_time else "00:00"

        for ep in fetcher.epdict.get(subject.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                # Generate UTC-aware datetime object
                utc_dt = util.genDateTime(ep.airdate, subject.broadcast_time)
                
                icl.setEvent(
                    # Title includes UTC time for reference
                    summary=f"[{utc_label}Z] " + util.genSummary(subject.name, subject.name_cn, ep.ep),
                    time=utc_dt,
                    uuid=util.genUUID(subject.id, ep.ep, userid),
                    descripion=util.genDec(subject.summary, ep.name_cn)
                )

    # 3. Write specifically to target.ics for GitHub Action to commit
    icl.write("target.ics")
    print(f"Successfully generated target.ics for user {userid}")