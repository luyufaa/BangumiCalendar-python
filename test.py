import util
from iCal import iCal
from reptile import data
import os

'''
Step 1: Get subscribed subjects via Username/ID
Step 2: Get episode info via Subject ID
Step 3: Merge info and export to target.ics
'''

if __name__ == '__main__':

    # Hardcoded for local testing convenience
    userid = "746322"
    
    # Initialize data fetcher
    data_fetcher = data(userid)
    
    # Step 1: Fetch subjects (includes bangumi-data lookup)
    data_fetcher.getsubjects()
    
    # Step 2: Fetch episodes
    data_fetcher.geteps()
    
    # Step 3: Integrate and export
    icl = iCal()
    offsets = util.load_offsets()
    
    for key in data_fetcher.subjects:
        offset_td = util.get_offset_timedelta(key, offsets)

        for i in data_fetcher.epdict[key.id]:
            # Check if airdate is valid YYYY-MM-DD
            if i.airdate and len(i.airdate) == 10:
                
                # Merge episode date and subject UTC broadcast time
                # Uses the updated util.genDateTime logic
                utc_time = util.genDateTime(i.airdate, key.broadcast_time)
                utc_time += offset_td
                
                icl.setEvent(
                    summary=util.genSummary(key.name, key.name_cn, i.ep),
                    time=utc_time,
                    uuid=util.genUUID(key.id, i.ep, userid),
                    description=util.genDec(key.summary, i.name_cn)
                )

    # Writes to target.ics for verification
    icl.write("target.ics")
    print("Local test complete. Created target.ics using UTC broadcast times.")
