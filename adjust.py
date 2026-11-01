#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BangumiCalendar 番剧播放时间与先行播放调整工具
支持交互式菜单管理与命令行一键调整，配置持久化保存至 offsets.json。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
import requests

import util
from reptile import data, PREFERRED_PLATFORMS, PLATFORM_NAMES, parse_iso
from iCal import iCal

def fetch_subject_info(subject_id):
    """从 Bangumi API 获取单个番剧信息"""
    url = f"https://api.bgm.tv/v0/subjects/{subject_id}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if 'id' in res:
            return res
    except Exception as e:
        print(f"获取番剧 {subject_id} 信息失败: {e}")
    return None

def format_dt(dt):
    """格式化 datetime 对象为易读字符串 (含周几)"""
    if not dt:
        return "未知"
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_str = weekdays[dt.weekday()]
    return f"{dt.strftime('%Y-%m-%d %H:%M')} ({weekday_str})"

def get_current_adjustment_desc(cfg):
    """获取当前配置的文字描述"""
    if not cfg:
        return "无自定义调整 (使用默认)"
    if isinstance(cfg, (int, float)):
        return f"微调偏移 {cfg} 分钟"
    if isinstance(cfg, str):
        return f"指定首播: {cfg}"
    if isinstance(cfg, dict):
        parts = []
        if cfg.get("platform"):
            p_name = util.get_platform_display_name(cfg["platform"])
            parts.append(f"强制平台: {p_name}")
        days = cfg.get("days") or cfg.get("offset_days")
        if days:
            if days < 0:
                parts.append(f"先行播放提前 {-days} 天")
            else:
                parts.append(f"延后 {days} 天")
        if cfg.get("time"):
            parts.append(f"播放时间: {cfg['time']}")
        if cfg.get("target_start"):
            parts.append(f"指定首播: {cfg['target_start']}")
        if cfg.get("episodes"):
            ep_parts = []
            for ep_k, ep_v in cfg["episodes"].items():
                if isinstance(ep_v, dict):
                    d = ep_v.get("date", "")
                    t = ep_v.get("time", "")
                    offs = ep_v.get("offset_days", "")
                    desc_s = f"第{ep_k}集: "
                    if d: desc_s += f"{d} "
                    if t: desc_s += f"{t} "
                    if offs: desc_s += f"(提前{-offs}天)" if offs < 0 else f"(延后{offs}天)"
                    ep_parts.append(desc_s.strip())
                else:
                    ep_parts.append(f"第{ep_k}集: {ep_v}")
            parts.append(f"单集先行: [{'; '.join(ep_parts)}]")
        return ", ".join(parts) if parts else "自定义字典配置"
    return str(cfg)

def print_banner():
    print("=" * 70)
    print("       📺 Bangumi 日历播放时间与先行播放调整工具")
    print("=" * 70)

def list_configured_offsets(offsets):
    """打印所有已在 offsets.json 中配置的番剧"""
    print("\n当前已保存的番剧调整配置 (offsets.json):")
    if not offsets:
        print("  (暂无任何调整配置)")
        return
    print("-" * 70)
    for sid, cfg in offsets.items():
        name = ""
        if isinstance(cfg, dict) and cfg.get("name"):
            name = f"《{cfg['name']}》"
        desc = get_current_adjustment_desc(cfg)
        print(f"  [ID: {sid:<7}] {name:<25} -> {desc}")
    print("-" * 70)

def run_generate_calendar(userid):
    """重新生成 target.ics 文件"""
    print(f"\n正在为用户 {userid} 重新生成日历 (target.ics)...")
    fetcher = data(userid)
    fetcher.getsubjects()
    fetcher.geteps()

    icl = iCal()
    offsets = util.load_offsets()

    count = 0
    for subject in fetcher.subjects:
        for ep in fetcher.epdict.get(subject.id, []):
            if ep.airdate and len(ep.airdate) == 10:
                event_dt = util.calculate_event_datetime(subject, ep, offsets)
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
                count += 1

    icl.write("target.ics")
    print(f"✅ 生成成功！共写入 {count} 个剧集日程到 target.ics")

def interactive_edit_subject(subject_obj, offsets, fetcher=None):
    """交互式编辑单个番剧的调整配置"""
    sid = str(subject_obj.id)
    title = subject_obj.name_cn or subject_obj.name

    while True:
        cfg = offsets.get(sid, {})
        if not isinstance(cfg, dict):
            # 将旧的简单数值/字符串转为 dict 以便修改
            old_val = cfg
            cfg = {"name": title}
            if isinstance(old_val, (int, float)):
                cfg["minutes"] = old_val
            elif isinstance(old_val, str):
                cfg["target_start"] = old_val

        # 计算当前第 1 集的实际播出时间
        # 构造一个虚拟的 Episode 1 或取真实第 1 集
        ep1_airdate = None
        if fetcher and sid in fetcher.epdict and fetcher.epdict[sid]:
            for ep_item in fetcher.epdict[sid]:
                if ep_item.airdate and len(ep_item.airdate) == 10:
                    ep1_airdate = ep_item.airdate
                    break
        if not ep1_airdate:
            ep1_airdate = (subject_obj.default_broadcast_time or subject_obj.broadcast_time or "2026-01-01")[:10]

        from reptile import Episode
        dummy_ep1 = Episode(1, "第1集", ep1_airdate)
        effective_dt = util.calculate_event_datetime(subject_obj, dummy_ep1, offsets)

        print("\n" + "=" * 70)
        print(f"🎬 编辑番剧: 《{title}》 (ID: {sid})")
        print("-" * 70)
        
        # 显示 TV 原版时间
        tv_time_str = "未知"
        if subject_obj.default_broadcast_time:
            tv_dt = parse_iso(subject_obj.default_broadcast_time)
            if tv_dt:
                tv_time_str = format_dt(tv_dt.astimezone(util.BEIJING_TZ))
        print(f"TV 原版播放时间: {tv_time_str}")

        # 显示可用的各流媒体平台时间
        print("可用放送平台时间:")
        if subject_obj.available_platforms:
            for p_code, ts in subject_obj.available_platforms.items():
                p_dt = parse_iso(ts)
                p_str = format_dt(p_dt.astimezone(util.BEIJING_TZ)) if p_dt else ts
                tag = " [当前自动选用]" if p_code == subject_obj.platform else ""
                print(f"  * {util.get_platform_display_name(p_code)} ({p_code}): {p_str}{tag}")
        else:
            print("  (未在 bangumi-data 中找到流媒体平台时间)")

        # 显示当前生效时间及调整
        cur_platform = cfg.get("platform") or subject_obj.platform
        print(f"当前生效播出时间: {format_dt(effective_dt)} [平台: {util.get_platform_display_name(cur_platform)}]")
        print(f"当前调整状态: {get_current_adjustment_desc(offsets.get(sid))}")
        print("-" * 70)
        print("请选择操作:")
        print("  [1] 调整播出日期偏移 (先行播放提前 X 天输入负数，如 -7 提前一周)")
        print("  [2] 调整播出时间 (例如设置为 23:30)")
        print("  [3] 指定首播完整日期时间 (例如 2026-10-01 22:30)")
        print("  [4] 切换播出平台 (巴哈姆特 / Netflix / Crunchyroll / TV原版)")
        print("  [5] 设置单集先行播放 (例如 第1集 提前到 2026-09-20 20:00)")
        print("  [6] 清除该番剧的所有调整 (恢复默认)")
        print("  [0] 完成并返回上级")
        print("=" * 70)

        choice = input("请输入选项数字: ").strip()

        if choice == '0' or not choice:
            break

        elif choice == '1':
            val = input("请输入调整的天数 (例如先行播放提前1周输入 -7，延后1天输入 1，输入 0 清除天数调整): ").strip()
            try:
                days_int = int(val)
                cfg["name"] = title
                if days_int == 0:
                    cfg.pop("days", None)
                    cfg.pop("offset_days", None)
                    print("已清除天数调整")
                else:
                    cfg["days"] = days_int
                    print(f"已设置日期偏移: {days_int} 天")
                offsets[sid] = cfg
                util.save_offsets(offsets)
            except ValueError:
                print("❌ 错误: 请输入有效的整数天数！")

        elif choice == '2':
            val = input("请输入每日播出时分 (格式 HH:MM，例如 23:30 或 21:00，留空清除): ").strip()
            if not val:
                cfg.pop("time", None)
                print("已清除时间调整")
            else:
                if re.match(r'^\d{1,2}:\d{2}$', val):
                    cfg["name"] = title
                    cfg["time"] = val
                    print(f"已设置播出时间为: {val}")
                else:
                    print("❌ 格式不正确，请使用 HH:MM 格式 (例如 23:30)")
            offsets[sid] = cfg
            util.save_offsets(offsets)

        elif choice == '3':
            val = input("请输入首播完整日期时间 (格式 YYYY-MM-DD HH:MM，留空清除): ").strip()
            if not val:
                cfg.pop("target_start", None)
                print("已清除指定首播时间")
            else:
                parsed = util.parse_target_start(val)
                if parsed:
                    cfg["name"] = title
                    cfg["target_start"] = val
                    print(f"已设置首播时间为: {val}")
                else:
                    print("❌ 格式不正确，请使用 YYYY-MM-DD HH:MM 格式！")
            offsets[sid] = cfg
            util.save_offsets(offsets)

        elif choice == '4':
            print("\n可选放送平台:")
            print("  [1] 巴哈姆特動畫瘋 (gamer)")
            print("  [2] Netflix (netflix)")
            print("  [3] Crunchyroll (crunchyroll)")
            print("  [4] TV 原版时间 (tv)")
            print("  [0] 取消强制平台设置 (恢复自动优选)")
            p_sel = input("请选择平台 [0-4]: ").strip()
            p_map = {'1': 'gamer', '2': 'netflix', '3': 'crunchyroll', '4': 'tv'}
            if p_sel in p_map:
                cfg["name"] = title
                cfg["platform"] = p_map[p_sel]
                print(f"已设置平台为: {util.get_platform_display_name(p_map[p_sel])}")
            elif p_sel == '0':
                cfg.pop("platform", None)
                print("已取消强制平台设置")
            offsets[sid] = cfg
            util.save_offsets(offsets)

        elif choice == '5':
            ep_str = input("请输入先行播放的集数 (例如 1): ").strip()
            if not ep_str:
                ep_str = "1"
            date_str = input(f"请输入第 {ep_str} 集播出日期 (格式 YYYY-MM-DD): ").strip()
            time_str = input(f"请输入第 {ep_str} 集播出时间 (格式 HH:MM，留空沿用系列时间): ").strip()

            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                print("❌ 日期格式不正确，请使用 YYYY-MM-DD")
                continue

            cfg["name"] = title
            if "episodes" not in cfg or not isinstance(cfg["episodes"], dict):
                cfg["episodes"] = {}

            ep_data = {"date": date_str}
            if time_str and re.match(r'^\d{1,2}:\d{2}$', time_str):
                ep_data["time"] = time_str

            cfg["episodes"][ep_str] = ep_data
            offsets[sid] = cfg
            util.save_offsets(offsets)
            print(f"✅ 已成功设置第 {ep_str} 集先行播放: {date_str} {time_str}")

        elif choice == '6':
            confirm = input("确定要清除该番剧的所有调整设置吗？(y/n): ").strip().lower()
            if confirm == 'y':
                offsets.pop(sid, None)
                util.save_offsets(offsets)
                print("✅ 已恢复默认配置！")

def interactive_mode():
    """交互式主入口"""
    print_banner()

    # 读取 USERID
    userid = os.environ.get("USERID")
    config = util.load_config()
    if not userid:
        userid = config.get("USERID")

    if not userid:
        print("\n提示: 未检测到 USERID 环境变量。")
        val = input("请输入你的 Bangumi 用户 ID 或 用户名 (留空可手动输入番剧ID查询): ").strip()
        if val:
            userid = val
            save_ans = input(f"是否将 USERID '{userid}' 保存到 config.json 以供本地重复使用？(y/n) [y]: ").strip().lower()
            if save_ans != 'n':
                config["USERID"] = userid
                util.save_config(config)

    offsets = util.load_offsets()

    fetcher = None
    if userid:
        print(f"\n正在从 Bangumi 获取用户 [{userid}] 的在看番剧列表...")
        fetcher = data(userid)
        fetcher.getsubjects()
        fetcher.geteps()
        print(f"✅ 成功获取到 {len(fetcher.subjects)} 部在看番剧。\n")

    while True:
        offsets = util.load_offsets()
        print("\n" + "=" * 70)
        if fetcher and fetcher.subjects:
            print(f"📋 当前在看番剧列表 (用户: {userid}):")
            print("-" * 70)
            print(f"{'序号':<5} {'ID':<8} {'当前平台':<12} {'当前状态':<15} {'番剧名称'}")
            print("-" * 70)
            for idx, sub in enumerate(fetcher.subjects, 1):
                sid = str(sub.id)
                cfg = offsets.get(sid)
                plat = cfg.get("platform") if isinstance(cfg, dict) and cfg.get("platform") else sub.platform
                plat_display = util.get_platform_display_name(plat)

                status_str = "默认"
                if sid in offsets:
                    status_str = "已自定义"
                elif sub.platform in ('gamer', 'gamer_hk', 'netflix', 'crunchyroll'):
                    status_str = "自动优选"

                title = sub.name_cn or sub.name
                if len(title) > 28:
                    title = title[:27] + "…"
                print(f"{idx:<5} {sid:<8} {plat_display:<12} {status_str:<15} {title}")
        else:
            print("📋 当前未加载用户番剧列表。")

        print("-" * 70)
        print("操作指令:")
        print("  [序号]  输入列表中番剧序号进行调整 (例如 1)")
        print("  id <ID> 直接输入任意 Bangumi 番剧 ID (例如 id 346425)")
        print("  s <关键词> 搜索番剧名称 (例如 s 迷宫)")
        print("  l 查看所有已调整配置")
        print("  g 立即生成/更新 target.ics 日历文件")
        print("  q 退出程序")
        print("=" * 70)

        cmd = input("请输入命令或序号: ").strip()
        if not cmd:
            continue

        if cmd.lower() in ('q', 'exit', 'quit'):
            print("👋 再见！")
            break

        if cmd.lower() in ('l', 'list'):
            list_configured_offsets(offsets)
            input("\n按回车键继续...")
            continue

        if cmd.lower() in ('g', 'generate'):
            if not userid:
                print("❌ 错误: 未设置 USERID，无法生成日历！")
            else:
                run_generate_calendar(userid)
            input("\n按回车键继续...")
            continue

        if cmd.lower().startswith('s ') or cmd.lower().startswith('search '):
            keyword = cmd.split(' ', 1)[1].strip()
            matched = []
            if fetcher:
                for idx, sub in enumerate(fetcher.subjects, 1):
                    if keyword.lower() in sub.name.lower() or keyword.lower() in (sub.name_cn or '').lower():
                        matched.append((idx, sub))
            if not matched:
                print(f"未找到包含 '{keyword}' 的番剧。")
            else:
                print(f"\n找到 {len(matched)} 部相关番剧:")
                for idx, sub in matched:
                    print(f"  [{idx}] {sub.id}: {sub.name_cn or sub.name}")
                sel = input("请输入要编辑的序号 (按回车取消): ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(fetcher.subjects):
                    interactive_edit_subject(fetcher.subjects[int(sel) - 1], offsets, fetcher)
            continue

        target_sid = None
        if cmd.lower().startswith('id '):
            target_sid = cmd.split(' ', 1)[1].strip()
        elif cmd.isdigit():
            idx = int(cmd)
            if fetcher and 1 <= idx <= len(fetcher.subjects):
                interactive_edit_subject(fetcher.subjects[idx - 1], offsets, fetcher)
                continue
            elif not fetcher:
                target_sid = cmd

        if target_sid:
            # 查找或请求该 ID 的番剧信息
            sub_found = None
            if fetcher:
                for s in fetcher.subjects:
                    if str(s.id) == target_sid:
                        sub_found = s
                        break
            if not sub_found:
                print(f"正在从 Bangumi 查询番剧 ID: {target_sid} ...")
                bgm_info = fetch_subject_info(target_sid)
                if bgm_info:
                    # 获取 bangumi-data
                    from reptile import Subject
                    temp_data = data("dummy")
                    temp_data.load_bangumi_data()
                    meta = temp_data.bgm_data_map.get(str(target_sid), {})
                    sub_found = Subject(
                        bgm_info['id'],
                        bgm_info['name'],
                        bgm_info.get('name_cn') or bgm_info['name'],
                        bgm_info.get('short_summary', ''),
                        meta.get('broadcast_time', ''),
                        default_broadcast_time=meta.get('default_broadcast_time', ''),
                        platform=meta.get('platform', 'default'),
                        available_platforms=meta.get('available_platforms', {})
                    )
            if sub_found:
                interactive_edit_subject(sub_found, offsets, fetcher)
            else:
                print(f"❌ 未能找到 ID 为 {target_sid} 的番剧信息。")

def cli_mode(args):
    """命令行参数直接执行模式"""
    offsets = util.load_offsets()

    if args.list:
        list_configured_offsets(offsets)
        return

    if args.generate:
        userid = args.user or os.environ.get("USERID") or util.load_config().get("USERID")
        if not userid:
            print("❌ 错误: 未指定 USERID，请使用 --user 参数或设置 USERID 环境变量。")
            sys.exit(1)
        run_generate_calendar(userid)
        return

    if not args.id:
        print("❌ 错误: 请使用 --id 指定番剧 ID，或运行无参数进入交互式菜单。")
        sys.exit(1)

    sid = str(args.id)
    cfg = offsets.get(sid, {})
    if not isinstance(cfg, dict):
        cfg = {"name": f"Subject {sid}"}

    if args.clear:
        if sid in offsets:
            del offsets[sid]
            util.save_offsets(offsets)
            print(f"✅ 已清除番剧 {sid} 的所有调整。")
        else:
            print(f"番剧 {sid} 暂无任何调整。")
        return

    updated = False

    if args.title:
        cfg["name"] = args.title
        updated = True

    if args.days is not None:
        cfg["days"] = args.days
        updated = True
        print(f"已设置日期偏移: {args.days} 天")

    if args.time:
        if not re.match(r'^\d{1,2}:\d{2}$', args.time):
            print("❌ 错误: 时间格式必须为 HH:MM (例如 23:30)")
            sys.exit(1)
        cfg["time"] = args.time
        updated = True
        print(f"已设置播放时间: {args.time}")

    if args.target_start:
        parsed = util.parse_target_start(args.target_start)
        if not parsed:
            print("❌ 错误: 首播时间格式不正确，请使用 YYYY-MM-DD HH:MM")
            sys.exit(1)
        cfg["target_start"] = args.target_start
        updated = True
        print(f"已设置首播时间: {args.target_start}")

    if args.platform:
        p = args.platform.lower()
        cfg["platform"] = p
        updated = True
        print(f"已设置播出平台: {util.get_platform_display_name(p)}")

    # 单集先行播放
    if args.ep is not None:
        ep_key = str(args.ep)
        if "episodes" not in cfg or not isinstance(cfg["episodes"], dict):
            cfg["episodes"] = {}
        ep_entry = cfg["episodes"].get(ep_key, {})
        if not isinstance(ep_entry, dict):
            ep_entry = {}

        if args.ep_date:
            ep_entry["date"] = args.ep_date
        if args.ep_time:
            ep_entry["time"] = args.ep_time
        if args.ep_days is not None:
            ep_entry["offset_days"] = args.ep_days

        cfg["episodes"][ep_key] = ep_entry
        updated = True
        print(f"已设置第 {ep_key} 集先行播放: {ep_entry}")

    if updated:
        offsets[sid] = cfg
        util.save_offsets(offsets)
        print(f"✅ 成功保存番剧 {sid} 的调整配置！")

        if args.auto_generate:
            userid = args.user or os.environ.get("USERID") or util.load_config().get("USERID")
            if userid:
                run_generate_calendar(userid)

def main():
    parser = argparse.ArgumentParser(
        description="Bangumi 日历播放时间与先行播放调整工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python adjust.py                                   # 启动交互式终端界面
  python adjust.py --list                            # 查看当前所有调整
  python adjust.py --id 346425 --days -7             # 将番剧 346425 提前 7 天 (先行播放)
  python adjust.py --id 346425 --time 23:30          # 将番剧 346425 播出时间改为 23:30
  python adjust.py --id 346425 --platform gamer      # 强制使用巴哈姆特平台时间
  python adjust.py --id 346425 --ep 1 --ep-date 2026-09-20 --ep-time 20:00 # 第1集先行播放
  python adjust.py --id 346425 --clear               # 清除该番剧的所有调整
  python adjust.py --generate --user 746322          # 重新生成 target.ics 文件
"""
    )
    parser.add_argument("-l", "--list", action="store_true", help="列出当前所有已保存的番剧调整配置")
    parser.add_argument("-i", "--id", type=str, help="指定 Bangumi 番剧 Subject ID")
    parser.add_argument("-d", "--days", type=int, help="播出日期偏移天数 (提前输入负数如 -7, 延后输入正数)")
    parser.add_argument("-t", "--time", type=str, help="播出具体时间 (格式 HH:MM，如 23:30)")
    parser.add_argument("--target-start", type=str, help="指定首播完整日期时间 (如 '2026-10-01 22:30')")
    parser.add_argument("-p", "--platform", type=str, choices=['gamer', 'netflix', 'crunchyroll', 'tv'], help="强制指定播出平台")
    parser.add_argument("--title", type=str, help="番剧名称备注")
    parser.add_argument("--clear", action="store_true", help="清除指定番剧的所有调整")
    parser.add_argument("--ep", type=int, help="指定集数 (用于单集先行播放)")
    parser.add_argument("--ep-date", type=str, help="该集先行播放的日期 (YYYY-MM-DD)")
    parser.add_argument("--ep-time", type=str, help="该集先行播放的时间 (HH:MM)")
    parser.add_argument("--ep-days", type=int, help="该集先行播放的偏移天数 (如 -7)")
    parser.add_argument("-g", "--generate", action="store_true", help="重新生成 target.ics 日历")
    parser.add_argument("-u", "--user", type=str, help="指定 Bangumi 用户 ID")
    parser.add_argument("--auto-generate", action="store_true", help="修改配置后自动重新生成日历")

    # 如果没有任何参数，进入交互式模式
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        args = parser.parse_args()
        cli_mode(args)

if __name__ == '__main__':
    main()
