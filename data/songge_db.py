#!/usr/bin/env python3
"""
松哥技能 - 客户数据库管理 v2
轻量画像 + 原始聊天分离存储
"""
import json
import os
import sys
import datetime
import gzip

DB_PATH = "/var/minis/skills/songge/data/clients.json"       # 轻量画像库
ARCHIVE_PATH = "/var/minis/skills/songge/data/chats_archive.json"  # 原始聊天档案

MAX_PROFILE_CHATS = 20  # 画像里最多保留最近20条摘要

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_archive():
    if not os.path.exists(ARCHIVE_PATH):
        return {}
    with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def save_archive(archive):
    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

def compress_archive():
    """压缩原始聊天档案"""
    if not os.path.exists(ARCHIVE_PATH):
        return
    # 读取原始JSON
    with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 写入压缩文件
    with gzip.open(ARCHIVE_PATH + ".gz", "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"✅ 已压缩为 {ARCHIVE_PATH}.gz")
    # 删除原文件
    os.remove(ARCHIVE_PATH)
    print(f"🗑️ 已删除原文件 {ARCHIVE_PATH}")

def load_compressed_archive():
    """读取压缩的档案"""
    gz_path = ARCHIVE_PATH + ".gz"
    if not os.path.exists(gz_path):
        return {}
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        return json.load(f)

# ============ 画像数据结构 ============
"""
客户画像结构：
{
    "name": "昵称",
    "stage": "关系阶段",
    "source": "来源渠道",
    "tags": ["标签1", "标签2"],
    "basic_info": {
        "age": "",
        "location": "",
        "job": "",
        "notes": ""
    },
    "personality": {
        "traits": [],        # 性格特点
        "communication": "", # 沟通风格
        "interests": []     # 兴趣点
    },
    "interaction": {
        "chat_count": 0,     # 累计聊天次数
        "date_count": 0,     # 累计约会次数
        "last_contact": "",  # 最近联系时间
        "response_rate": "", # 回复率
        "avg_response_time": "" # 平均回复时间
    },
    "patterns": {
        "strengths": [],     # 她的雷点（不能踩）
        "weaknesses": [],   # 她的窗口（可以打）
        "favorite_topics": [], # 她感兴趣的话题
        "rejection_patterns": [] # 拒绝模式
    },
    "milestones": [],       # 关系里程碑
    "chats_summary": [],    # 最近20条聊天摘要（精简版）
    "created": "",
    "updated": ""
}

聊天摘要结构：
{
    "date": "",
    "scene": "",
    "your_msg": "",
    "her_msg": "",
    "result": "",   # 结果描述
    "lesson": ""   # 学到的点
}
"""

def create_profile(name, source="", stage="初识", tags=None, basic_info=None):
    """创建新客户画像"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "name": name,
        "stage": stage,
        "source": source,
        "tags": tags or [],
        "basic_info": basic_info or {"location": "", "job": "", "notes": ""},
        "personality": {
            "traits": [],
            "communication": "",
            "interests": []
        },
        "interaction": {
            "chat_count": 0,
            "date_count": 0,
            "last_contact": now[:10],
            "response_rate": "",
            "avg_response_time": ""
        },
        "patterns": {
            "strengths": [],
            "weaknesses": [],
            "favorite_topics": [],
            "rejection_patterns": []
        },
        "milestones": [],
        "chats_summary": [],
        "created": now,
        "updated": now
    }

# ============ 命令处理 ============

def cmd_list(args):
    """列出所有客户"""
    db = load_db()
    if not db:
        print("📭 暂无客户数据")
        return
    
    print(f"\n📋 客户画像列表（共 {len(db)} 人）\n")
    print(f"{'昵称':<10} {'阶段':<6} {'来源':<10} {'聊天':<4} {'最近联系'}")
    print("-" * 50)
    for i, (name, info) in enumerate(sorted(db.items()), 1):
        stage = info.get("stage", "未知")
        source = info.get("source", "")[:8]
        chats = len(info.get("chats_summary", []))
        last = info.get("interaction", {}).get("last_contact", "无")[:10]
        print(f"{i:<2} {name:<10} {stage:<6} {source:<10} {chats:<4} {last}")
    print()

def cmd_add(args):
    """添加/更新客户画像"""
    db = load_db()
    name = args.name
    
    if name in db:
        print(f"⚠️  客户 [{name}] 已存在，将更新信息")
    else:
        db[name] = create_profile(
            name=name,
            source=args.source or "",
            stage=args.stage or "初识",
            tags=args.tags.split(",") if args.tags else []
        )
    
    # 更新基本信息
    if args.notes:
        db[name]["basic_info"]["notes"] = args.notes
    if args.location:
        db[name]["basic_info"]["location"] = args.location
    if args.job:
        db[name]["basic_info"]["job"] = args.job
    if args.stage:
        db[name]["stage"] = args.stage
    
    db[name]["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    save_db(db)
    print(f"✅ 客户 [{name}] 画像已保存")
    print_profile(db[name])

def cmd_addchat(args):
    """追加聊天摘要（轻量版）"""
    db = load_db()
    name = args.name
    
    if name not in db:
        print(f"❌ 客户 [{name}] 不存在，请先添加")
        return
    
    # 创建聊天摘要
    chat_summary = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "scene": args.scene or "",
        "your_msg": args.your,
        "her_msg": args.her,
        "result": args.result or "",
        "lesson": args.lesson or ""
    }
    
    # 添加到画像的摘要列表
    db[name]["chats_summary"].append(chat_summary)
    
    # 只保留最近20条
    if len(db[name]["chats_summary"]) > MAX_PROFILE_CHATS:
        db[name]["chats_summary"] = db[name]["chats_summary"][-MAX_PROFILE_CHATS:]
    
    # 更新互动统计
    db[name]["interaction"]["chat_count"] += 1
    db[name]["interaction"]["last_contact"] = chat_summary["date"]
    db[name]["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 如果指定了结果，提取pattern
    if args.result:
        db[name] = extract_patterns(db[name], chat_summary)
    
    save_db(db)
    print(f"✅ 聊天摘要已追加到 [{name}]")
    print(f"   当前摘要数: {len(db[name]['chats_summary'])}")

def extract_patterns(profile, chat):
    """从聊天中提取模式"""
    result = chat.get("result", "").lower()
    her_msg = chat.get("her_msg", "").lower()
    scene = chat.get("scene", "").lower()
    
    # 识别她的反应模式
    if any(x in her_msg for x in ["哈哈", "笑", "开心"]):
        profile["patterns"]["weaknesses"].append("喜欢被逗笑")
    if any(x in her_msg for x in ["不想", "不了", "算了"]):
        profile["patterns"]["rejection_patterns"].append("会先拒绝试探")
    if any(x in result for x in ["邀约成功", "答应", "可以"]):
        profile["milestones"].append({"type": "invitation", "date": chat["date"], "scene": scene})
    
    # 识别感兴趣话题
    if "咖啡" in her_msg or "咖啡" in scene:
        profile["personality"]["interests"].append("咖啡")
    if "拍照" in her_msg or "拍照" in scene:
        profile["personality"]["interests"].append("拍照")
    
    return profile

def cmd_view(args):
    """查看客户画像"""
    db = load_db()
    name = args.name
    
    if name not in db:
        print(f"❌ 客户 [{name}] 不存在")
        return
    
    print_profile(db[name])

def print_profile(info):
    """打印完整画像"""
    print(f"\n{'='*50}")
    print(f"👤 {info['name']}")
    print(f"{'='*50}")
    print(f"📌 阶段: {info['stage']} | 来源: {info['source']}")
    print(f"🏷️  标签: {', '.join(info['tags']) if info['tags'] else '无'}")
    print()
    
    print(f"📋 基本信息:")
    bi = info.get("basic_info", {})
    if bi.get("location"): print(f"   地点: {bi['location']}")
    if bi.get("job"): print(f"   职业: {bi['job']}")
    if bi.get("notes"): print(f"   备注: {bi['notes']}")
    print()
    
    p = info.get("personality", {})
    if p.get("traits"): print(f"🧠 性格: {', '.join(p['traits'])}")
    if p.get("communication"): print(f"💬 沟通: {p['communication']}")
    if p.get("interests"): print(f"❤️ 兴趣: {', '.join(set(p['interests']))}")
    print()
    
    i = info.get("interaction", {})
    print(f"📊 互动:")
    print(f"   聊天次数: {i.get('chat_count', 0)}")
    print(f"   约会次数: {i.get('date_count', 0)}")
    print(f"   最近联系: {i.get('last_contact', '无')}")
    print()
    
    patterns = info.get("patterns", {})
    if patterns.get("strengths"): print(f"⚠️  雷点: {', '.join(patterns['strengths'])}")
    if patterns.get("weaknesses"): print(f"💗 窗口: {', '.join(set(patterns['weaknesses']))}")
    if patterns.get("favorite_topics"): print(f"📝 兴趣话题: {', '.join(patterns['favorite_topics'])}")
    if patterns.get("rejection_patterns"): print(f"🚫 拒绝模式: {', '.join(patterns['rejection_patterns'])}")
    print()
    
    if info.get("milestones"):
        print(f"🎯 里程碑:")
        for m in info["milestones"][-3:]:
            print(f"   - [{m.get('date', '')}] {m.get('type', '')}: {m.get('scene', '')}")
        print()
    
    if info.get("chats_summary"):
        print(f"📝 最近聊天摘要 ({len(info['chats_summary'])}条):")
        print("-" * 50)
        for i, chat in enumerate(info["chats_summary"][-5:], 1):
            print(f"\n  [{chat['date']}] {chat['scene']}")
            print(f"    你: {chat['your_msg'][:30]}...")
            print(f"    她: {chat['her_msg'][:30]}...")
            if chat.get("result"):
                print(f"    结果: {chat['result']}")
        print()
    
    print(f"创建: {info.get('created', '')} | 更新: {info.get('updated', '')}")

def cmd_search(args):
    """搜索客户"""
    db = load_db()
    keyword = args.keyword
    
    results = []
    for name, info in db.items():
        # 匹配昵称
        if keyword.lower() in name.lower():
            results.append((name, info, "昵称"))
            continue
        # 匹配标签
        for tag in info.get("tags", []):
            if keyword.lower() in tag.lower():
                results.append((name, info, f"标签: {tag}"))
                break
        # 匹配兴趣
        for interest in info.get("personality", {}).get("interests", []):
            if keyword.lower() in interest.lower():
                results.append((name, info, f"兴趣: {interest}"))
                break
        # 匹配备注
        if keyword.lower() in str(info.get("basic_info", {}).get("notes", "")).lower():
            results.append((name, info, "备注"))
    
    if not results:
        print(f"❌ 未找到 [{keyword}] 相关客户")
        return
    
    print(f"\n🔍 搜索结果 ({len(results)} 条)\n")
    for name, info, reason in results:
        print(f"👤 {name} | {info['stage']} | {reason}")
        print(f"   {info['updated'][:10]} | 聊天{info['interaction']['chat_count']}次")

def cmd_archive(args):
    """存档原始聊天"""
    db = load_db()
    archive = load_archive()
    name = args.name
    
    if name not in db:
        print(f"❌ 客户 [{name}] 不存在")
        return
    
    if not args.your and not args.her:
        print("❌ 请提供聊天内容 (-u 你的话 -g 她的话)")
        return
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if name not in archive:
        archive[name] = {"raw_chats": [], "created": now}
    
    archive[name]["raw_chats"].append({
        "timestamp": now,
        "scene": args.scene or "",
        "your_msg": args.your,
        "her_msg": args.her,
        "your_action": args.action or "",
        "result": args.result or ""
    })
    archive[name]["updated"] = now
    
    save_archive(archive)
    print(f"✅ 原始聊天已存档到 [{name}]")
    print(f"   当前原始记录: {len(archive[name]['raw_chats'])}条")

def cmd_view_archive(args):
    """查看原始聊天档案"""
    # 优先读压缩版
    if os.path.exists(ARCHIVE_PATH + ".gz"):
        archive = load_compressed_archive()
    else:
        archive = load_archive()
    
    name = args.name
    if name not in archive:
        print(f"❌ 客户 [{name}] 无原始档案")
        return
    
    chats = archive[name].get("raw_chats", [])
    print(f"\n📜 [{name}] 原始聊天档案（共 {len(chats)} 条）")
    print("-" * 50)
    
    # 分页显示
    start = args.start or 0
    end = start + 10
    for i, chat in enumerate(chats[start:end], start + 1):
        print(f"\n[{i}] {chat.get('timestamp', '')}")
        print(f"    场景: {chat.get('scene', '')}")
        print(f"    你: {chat.get('your_msg', '')}")
        print(f"    她: {chat.get('her_msg', '')}")
        if chat.get("your_action"):
            print(f"    回复: {chat.get('your_action', '')}")
        if chat.get("result"):
            print(f"    结果: {chat.get('result', '')}")
    
    if len(chats) > end:
        print(f"\n... 还有 {len(chats) - end} 条，查看更多: view_archive -n {name} --start {end}")

def cmd_compress(args):
    """压缩原始聊天档案"""
    compress_archive()

def cmd_setstage(args):
    """设置关系阶段"""
    db = load_db()
    name = args.name
    
    if name not in db:
        print(f"❌ 客户 [{name}] 不存在")
        return
    
    stages = ["初识", "熟悉", "暧昧", "已确定"]
    if args.stage not in stages:
        print(f"❌ 阶段必须是: {', '.join(stages)}")
        return
    
    old_stage = db[name]["stage"]
    db[name]["stage"] = args.stage
    db[name]["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save_db(db)
    print(f"✅ [{name}] {old_stage} → {args.stage}")

def cmd_stats(args):
    """数据统计"""
    db = load_db()
    if not db:
        print("📭 暂无数据")
        return
    
    stages = {"初识": 0, "熟悉": 0, "暧昧": 0, "已确定": 0}
    total_chats = 0
    for info in db.values():
        s = info.get("stage", "未知")
        if s in stages: stages[s] += 1
        total_chats += info.get("interaction", {}).get("chat_count", 0)
    
    print(f"\n📊 画像数据库统计\n")
    print(f"客户总数: {len(db)}")
    print(f"累计聊天: {total_chats}")
    print(f"画像文件: {DB_PATH} ({os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0} bytes)")
    
    gz_path = ARCHIVE_PATH + ".gz"
    if os.path.exists(gz_path):
        print(f"原始档案: {gz_path} ({os.path.getsize(gz_path)} bytes)")
    elif os.path.exists(ARCHIVE_PATH):
        print(f"原始档案: {ARCHIVE_PATH} ({os.path.getsize(ARCHIVE_PATH)} bytes)")
    
    print(f"\n阶段分布:")
    for stage, count in stages.items():
        bar = "█" * count + "░" * max(0, len(db) - count) if db else ""
        print(f"  {stage}: {count} 人 {bar}")
    print()

def cmd_export(args):
    """导出画像数据"""
    db = load_db()
    print(json.dumps(db, ensure_ascii=False, indent=2))

def cmd_del(args):
    """删除客户"""
    db = load_db()
    archive = load_archive()
    name = args.name
    
    if name not in db:
        print(f"❌ 客户 [{name}] 不存在")
        return
    
    confirm = input(f"⚠️ 确认删除 [{name}] 的画像？(y/n): ")
    if confirm.lower() != 'y':
        print("取消")
        return
    
    del db[name]
    save_db(db)
    
    # 询问是否删除原始档案
    if name in archive:
        confirm2 = input("是否也删除原始聊天档案？(y/n): ")
        if confirm2.lower() == 'y':
            del archive[name]
            save_archive(archive)
    
    print(f"✅ 已删除 [{name}]")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="松哥技能 - 客户画像数据库")
    subparsers = parser.add_subparsers(dest="cmd", help="子命令")
    
    # list
    p_list = subparsers.add_parser("list", help="列出所有客户")
    p_list.set_defaults(func=cmd_list)
    
    # add
    p_add = subparsers.add_parser("add", help="添加/更新客户画像")
    p_add.add_argument("-n", "--name", required=True, help="客户昵称")
    p_add.add_argument("-s", "--stage", help="关系阶段")
    p_add.add_argument("-q", "--source", help="来源渠道")
    p_add.add_argument("-t", "--tags", help="标签")
    p_add.add_argument("-l", "--location", help="地点")
    p_add.add_argument("-j", "--job", help="职业")
    p_add.add_argument("-m", "--notes", help="备注")
    p_add.set_defaults(func=cmd_add)
    
    # addchat
    p_chat = subparsers.add_parser("addchat", help="追加聊天摘要")
    p_chat.add_argument("-n", "--name", required=True, help="客户昵称")
    p_chat.add_argument("-u", "--your", required=True, help="你说的话")
    p_chat.add_argument("-g", "--her", required=True, help="她说的话")
    p_chat.add_argument("-c", "--scene", help="场景")
    p_chat.add_argument("-r", "--result", help="结果")
    p_chat.add_argument("-l", "--lesson", help="学到的点")
    p_chat.set_defaults(func=cmd_addchat)
    
    # view
    p_view = subparsers.add_parser("view", help="查看客户画像")
    p_view.add_argument("-n", "--name", required=True, help="客户昵称")
    p_view.set_defaults(func=cmd_view)
    
    # search
    p_search = subparsers.add_parser("search", help="搜索客户")
    p_search.add_argument("-k", "--keyword", required=True, help="关键词")
    p_search.set_defaults(func=cmd_search)
    
    # archive
    p_arch = subparsers.add_parser("archive", help="存档原始聊天")
    p_arch.add_argument("-n", "--name", required=True, help="客户昵称")
    p_arch.add_argument("-u", "--your", help="你说的话")
    p_arch.add_argument("-g", "--her", help="她说的话")
    p_arch.add_argument("-c", "--scene", help="场景")
    p_arch.add_argument("-a", "--action", help="你的回复")
    p_arch.add_argument("-r", "--result", help="结果")
    p_arch.set_defaults(func=cmd_archive)
    
    # view_archive
    p_varch = subparsers.add_parser("view_archive", help="查看原始聊天档案")
    p_varch.add_argument("-n", "--name", required=True, help="客户昵称")
    p_varch.add_argument("--start", type=int, help="起始位置")
    p_varch.set_defaults(func=cmd_view_archive)
    
    # compress
    p_comp = subparsers.add_parser("compress", help="压缩原始聊天档案")
    p_comp.set_defaults(func=cmd_compress)
    
    # setstage
    p_stage = subparsers.add_parser("setstage", help="设置关系阶段")
    p_stage.add_argument("-n", "--name", required=True, help="客户昵称")
    p_stage.add_argument("-s", "--stage", required=True, help="阶段")
    p_stage.set_defaults(func=cmd_setstage)
    
    # stats
    p_stats = subparsers.add_parser("stats", help="数据统计")
    p_stats.set_defaults(func=cmd_stats)
    
    # export
    p_exp = subparsers.add_parser("export", help="导出画像数据")
    p_exp.set_defaults(func=cmd_export)
    
    # del
    p_del = subparsers.add_parser("del", help="删除客户")
    p_del.add_argument("-n", "--name", required=True, help="客户昵称")
    p_del.set_defaults(func=cmd_del)
    
    args = parser.parse_args()
    if args.cmd and hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
