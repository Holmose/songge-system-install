#!/usr/bin/env python3
"""
松哥技能 - 快速查询脚本 v2
支持画像库 + 原始档案查询
"""
import json
import os
import sys
import gzip

DB_PATH = "/var/minis/skills/songge/data/clients.json"
ARCHIVE_PATH = "/var/minis/skills/songge/data/chats_archive.json"

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_archive():
    gz_path = ARCHIVE_PATH + ".gz"
    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            return json.load(f)
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def query_client(name_hint):
    """查询客户画像"""
    db = load_db()
    if not db:
        return None
    
    # 精确匹配
    if name_hint in db:
        return name_hint, db[name_hint]
    
    # 模糊匹配
    name_lower = name_hint.lower()
    for name, info in db.items():
        if name_lower in name.lower() or name.lower() in name_lower:
            return name, info
    
    return None, None

def get_all_clients():
    """获取所有客户列表"""
    db = load_db()
    return [(name, info.get("stage", ""), info.get("updated", "")[:10]) 
            for name, info in sorted(db.items())]

def search_clients(keyword):
    """搜索客户"""
    db = load_db()
    results = []
    
    for name, info in db.items():
        match_reason = None
        match_type = ""
        
        # 匹配昵称
        if keyword.lower() in name.lower():
            match_reason = name
            match_type = "昵称"
        
        # 匹配标签
        if not match_reason:
            for tag in info.get("tags", []):
                if keyword.lower() in tag.lower():
                    match_reason = f"标签:{tag}"
                    match_type = "标签"
                    break
        
        # 匹配兴趣
        if not match_reason:
            for interest in info.get("personality", {}).get("interests", []):
                if keyword.lower() in interest.lower():
                    match_reason = f"兴趣:{interest}"
                    match_type = "兴趣"
                    break
        
        # 匹配备注
        if not match_reason:
            notes = str(info.get("basic_info", {}).get("notes", ""))
            if keyword.lower() in notes.lower():
                match_reason = notes[:30]
                match_type = "备注"
        
        if match_reason:
            results.append((name, info, match_type, match_reason))
    
    return results

def print_brief_profile(name, info):
    """打印简短画像"""
    print(f"\n{'='*50}")
    print(f"👤 {name}")
    print(f"{'='*50}")
    print(f"📌 阶段: {info.get('stage', '')} | 来源: {info.get('source', '')}")
    print(f"🏷️  标签: {', '.join(info['tags']) if info['tags'] else '无'}")
    
    bi = info.get("basic_info", {})
    if bi.get("location") or bi.get("job") or bi.get("notes"):
        print(f"\n📋 基本:")
        if bi.get("location"): print(f"   地点: {bi['location']}")
        if bi.get("job"): print(f"   职业: {bi['job']}")
        if bi.get("notes"): print(f"   备注: {bi['notes']}")
    
    p = info.get("personality", {})
    if p.get("interests"):
        interests = list(set(p["interests"]))
        print(f"❤️ 兴趣: {', '.join(interests)}")
    
    patterns = info.get("patterns", {})
    if patterns.get("strengths"):
        wins = list(set(patterns["strengths"]))
        print(f"💗 可接点: {', '.join(wins)}")
    if patterns.get("weaknesses"):
        print(f"⚠️ 风险点: {', '.join(patterns['weaknesses'])}")
    if patterns.get("rejection_patterns"):
        print(f"🚫 拒绝: {', '.join(patterns['rejection_patterns'])}")
    
    i = info.get("interaction", {})
    print(f"\n📊 互动: 聊天{i.get('chat_count',0)}次 | 约会{i.get('date_count',0)}次 | 最近{i.get('last_contact','无')}")
    
    if info.get("chats_summary"):
        print(f"\n📝 最近聊天 ({len(info['chats_summary'])}条摘要):")
        for chat in info["chats_summary"][-3:]:
            print(f"   [{chat['date']}] {chat['scene']}")
            print(f"     你: {chat['your_msg'][:25]}...")
            print(f"     她: {chat['her_msg'][:25]}...")

    status = info.get("当前状态", {})
    if isinstance(status, dict):
        print("\n🎯 当前状态:")
        print(f"   阶段: {status.get('阶段', status.get('阶段判断', ''))}")
        print(f"   配合度: {status.get('配合度', '')} | 窗口: {status.get('窗口', status.get('窗口等级', ''))}")
        print(f"   风险: {status.get('风险', '')}")
        print(f"   推荐动作: {status.get('推荐动作', '')} | 禁止动作: {status.get('禁止动作', '')}")
        if status.get('依据'):
            print(f"   依据: {status.get('依据')}")
    if info.get("raw_chat_files") or info.get("case_ids"):
        print("\n🔗 关联:")
        if info.get("raw_chat_files"):
            print(f"   raw: {', '.join(info.get('raw_chat_files', []))}")
        if info.get("case_ids"):
            print(f"   cases: {', '.join(info.get('case_ids', []))}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 songge_query.py --list                # 列出所有客户")
        print("  python3 songge_query.py <昵称>                 # 查询客户画像")
        print("  python3 songge_query.py --search <关键词>       # 搜索客户")
        print("  python3 songge_query.py --archive <昵称>        # 查看原始聊天档案")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "--list":
        clients = get_all_clients()
        if not clients:
            print("📭 暂无客户数据")
        else:
            print(f"\n📋 客户画像列表（共 {len(clients)} 人）\n")
            print(f"{'昵称':<12} {'阶段':<6} {'最近更新'}")
            print("-" * 30)
            for name, stage, updated in clients:
                print(f"{name:<12} {stage:<6} {updated}")
        print()
    
    elif cmd == "--search":
        if len(sys.argv) < 3:
            print("请提供搜索关键词")
            sys.exit(1)
        keyword = sys.argv[2]
        results = search_clients(keyword)
        if not results:
            print(f"❌ 未找到 [{keyword}] 相关客户")
        else:
            print(f"\n🔍 搜索 [{keyword}] ({len(results)} 条)\n")
            for name, info, mtype, reason in results:
                i = info.get("interaction", {})
                print(f"👤 {name} | {info['stage']} | {mtype}: {reason}")
                print(f"   聊天{i.get('chat_count',0)}次 | {info['updated'][:10]}")
        print()
    
    elif cmd == "--archive":
        if len(sys.argv) < 3:
            print("请提供客户昵称")
            sys.exit(1)
        name = sys.argv[2]
        archive = load_archive()
        if name not in archive:
            print(f"❌ 客户 [{name}] 无原始聊天档案")
            sys.exit(1)
        
        chats = archive[name].get("raw_chats", [])
        print(f"\n📜 [{name}] 原始聊天档案（共 {len(chats)} 条）")
        print("-" * 50)
        
        # 显示最近10条
        for i, chat in enumerate(chats[-10:], max(1, len(chats)-9)):
            print(f"\n[{i}] {chat.get('timestamp', '')}")
            print(f"    你: {chat.get('your_msg', '')}")
            print(f"    她: {chat.get('her_msg', '')}")
        print()
    
    else:
        # 尝试查询客户画像
        name_hint = cmd
        name, info = query_client(name_hint)
        
        if not name:
            print(f"❌ 未找到客户 [{name_hint}]")
            print("\n💡 试试 --list 查看所有客户，或 --search 搜索")
            sys.exit(1)
        
        print_brief_profile(name, info)
        print()
