import util
from iCal import iCal
from reptile import data
import os

'''
step 1 通过用户名获取订阅的番组id
step 2 通过番组id获取章节信息
step 3 将信息进行整合导出到ics
'''

if __name__ == '__main__':

    # Hardcoded ID as per your original file
    userid = "746322" 
    data_fetcher = data(userid)
    
    # step 1 通过用户名获取订阅的番组id (Internal logic now loads bangumi-data)
    data_fetcher.getsubjects()
    
    # step 2 通过番组id获取章节信息
    data_fetcher.geteps()
    
    # 将信息进行整合导出到 target.ics
    icl = iCal()
    
    for key in data_fetcher.subjects:
        # Extract the HH:MM label from the ISO broadcast_time string
        # e.g., "2024-01-05T14:30:00.000Z" -> "14:30"
        time_label = key.broadcast_time[11:16] if key.broadcast_time else "00:00"

        for i in data_fetcher.epdict[key.id]:
            # 判定日历格式是否正确
            if len(i.airdate) == 10:
                # Use genDateTime to combine airdate and broadcast_time
                precise_time = util.genDateTime(i.airdate, key.broadcast_time)
                
                icl.setEvent(
                    # Added the [Time] prefix to the summary
                    summary=f"[{time_label}] " + util.genSummary(key.name, key.name_cn, i.ep),
                    time=precise_time,
                    uuid=util.genUUID(key.id, i.ep, userid),
                    descripion=util.genDec(key.summary, i.name_cn)
                )

    # Modified to write specifically to target.ics for GitHub Action compatibility
    icl.write("target.ics")
    print("Done! target.ics has been generated with play times.")