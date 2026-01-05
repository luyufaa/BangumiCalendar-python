import util
from iCal import iCal
from reptile import data
import os

if __name__ == '__main__':
    userid = os.environ.get("USERID")
    if not userid:
        print("Error: USERID secret not found.")
        exit(1)

    fetcher = data(userid)
    fetcher.getsubjects()
    fetcher.geteps()
    
    icl = iCal()
    for sub in fetcher.subjects:
        for ep in fetcher.epdict.get(sub.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                # Get the localized Beijing time
                beijing_dt = util.genDateTime(ep.airdate, sub.broadcast_time)
                
                icl.setEvent(
                    summary=util.genSummary(sub.name, sub.name_cn, ep.ep),
                    time=beijing_dt,
                    uuid=util.genUUID(sub.id, ep.ep, userid),
                    description=util.genDec(sub.summary, ep.name_cn)
                )

    icl.write("target.ics")
    print("Successfully generated target.ics")
