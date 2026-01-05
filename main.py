import util
from iCal import iCal
from reptile import data
import os

if __name__ == '__main__':
    # Use environment variable for GitHub Actions compatibility
    userid = os.environ.get("USERID")
    if not userid:
        print("Error: USERID environment variable not found.")
        exit(1)

    # 1. Fetch Data
    fetcher = data(userid)
    fetcher.getsubjects()
    fetcher.geteps()
    
    # 2. Build Calendar
    icl = iCal()
    for sub in fetcher.subjects:
        # Get HH:MM for the label
        time_label = sub.broadcast_time[11:16] if sub.broadcast_time else "00:00"

        for ep in fetcher.epdict.get(sub.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                # IMPORTANT: Pass both date AND the broadcast time info
                localized_dt = util.genDateTime(ep.airdate, sub.broadcast_time)
                
                icl.setEvent(
                    summary=f"[{time_label}] " + util.genSummary(sub.name, sub.name_cn, ep.ep),
                    time=localized_dt,
                    uuid=util.genUUID(sub.id, ep.ep, userid),
                    descripion=util.genDec(sub.summary, ep.name_cn)
                )

    # 3. Output to target.ics
    icl.write("target.ics")
    print(f"Generated target.ics for user {userid}")