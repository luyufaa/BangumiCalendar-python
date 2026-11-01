import util
from iCal import iCal
from reptile import data
import os

'''
Step 1: Get subscribed subjects via Username/ID
Step 2: Get episode info via Subject ID
Step 3: Merge info, apply platform priority & offsets, and export to target.ics
'''

if __name__ == '__main__':

    # Hardcoded for local testing convenience, or from env / config
    userid = os.environ.get("USERID")
    if not userid:
        config = util.load_config()
        userid = config.get("USERID", "746322")

    # Initialize data fetcher
    data_fetcher = data(userid)

    # Step 1: Fetch subjects (includes bangumi-data lookup with 巴哈姆特, Netflix, CR priority)
    data_fetcher.getsubjects()

    # Step 2: Fetch episodes
    data_fetcher.geteps()

    # Step 3: Integrate and export
    icl = iCal()
    offsets = util.load_offsets()

    print(f"\nProcessing {len(data_fetcher.subjects)} subjects for user {userid}:")
    for key in data_fetcher.subjects:
        cfg = offsets.get(str(key.id))
        active_platform = key.platform
        if isinstance(cfg, dict) and "platform" in cfg:
            active_platform = cfg["platform"]

        plat_name = util.get_platform_display_name(active_platform)
        print(f" - [{key.id}] {key.name_cn or key.name} (平台: {plat_name})")

        for i in data_fetcher.epdict.get(key.id, []):
            if i.airdate and len(i.airdate) == 10:
                event_dt = util.calculate_event_datetime(key, i, offsets)

                icl.setEvent(
                    summary=util.genSummary(key.name, key.name_cn, i.ep),
                    time=event_dt,
                    uuid=util.genUUID(key.id, i.ep, userid),
                    description=util.genDec(key.summary, i.name_cn, active_platform)
                )

    # Writes to target.ics for verification
    icl.write("target.ics")
    print(f"\nLocal test complete. Created target.ics using prioritized platform times and offsets.")
