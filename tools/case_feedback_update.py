#!/usr/bin/env python3
"""
松哥案例反馈闭环工具

用途：输入案例编号和反馈结果，自动更新：
- 05-case-index.md 结果标签、统计区、最近更新
- 12-scene-reply-library.md 话术验证索引（正反馈时）
- clients.json 中匹配 case_id 的客户当前状态依据/updated

只修改索引/客户状态/验证索引，不修改 raw 原始聊天。

用法：
  python3 case_feedback_update.py CASE_ID RESULT [--client NAME] [--note TEXT]

RESULT: 未发送 / 正反馈 / 普通反馈 / 冷淡 / 翻车 / 待反馈 / 待验证
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

CASE_INDEX = Path('/var/minis/memory/songge/05-case-index.md')
SCENE_LIB = Path('/var/minis/memory/songge/knowledge/12-scene-reply-library.md')
CLIENTS = Path('/var/minis/skills/songge/data/clients.json')

VALID_RESULTS = {'未发送', '正反馈', '普通反馈', '冷淡', '翻车', '待反馈', '待验证'}
SCENE_LABELS = {
    'body','mood','test','looks','silent','flat','cold','noreply','distance',
    'reject_relation','public','identity','warmup','date','fix','other'
}


def split_row(line: str):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def build_row(cols):
    return '| ' + ' | '.join(cols) + ' |'


def parse_rows(text: str):
    rows = []
    for idx, line in enumerate(text.splitlines()):
        if line.startswith('| 202'):
            cols = split_row(line)
            if len(cols) >= 11 and re.match(r'^\d{4}-\d{2}-\d{2}', cols[0]):
                rows.append((idx, cols[:11]))
    return rows


def update_case_index(case_id: str, result: str, note: str = ''):
    text = CASE_INDEX.read_text(encoding='utf-8')
    lines = text.splitlines()
    rows = parse_rows(text)
    found = None
    for idx, cols in rows:
        if cols[0] == case_id:
            found = (idx, cols)
            break
    if not found:
        raise SystemExit(f'未找到案例编号：{case_id}')
    idx, cols = found
    old_result = cols[9]
    cols[9] = result
    if note:
        if note not in cols[10]:
            cols[10] = cols[10] + '；反馈：' + note
    lines[idx] = build_row(cols)

    # Reparse from updated lines
    new_rows = []
    for line in lines:
        if line.startswith('| 202'):
            c = split_row(line)
            if len(c) >= 11 and re.match(r'^\d{4}-\d{2}-\d{2}', c[0]):
                new_rows.append(c[:11])
    counts = Counter(r[9] for r in new_rows)
    stats_map = {
        '总案例数': len(new_rows),
        '已发送-正反馈': counts.get('正反馈', 0),
        '已发送-普通反馈': counts.get('普通反馈', 0),
        '已发送-冷淡': counts.get('冷淡', 0),
        '已发送-翻车': counts.get('翻车', 0),
        '未发送': counts.get('未发送', 0),
        '待反馈': counts.get('待反馈', 0),
        '待验证': counts.get('待验证', 0),
    }
    for i, line in enumerate(lines):
        m = re.match(r'\| (总案例数|已发送-正反馈|已发送-普通反馈|已发送-冷淡|已发送-翻车|未发送|待反馈|待验证) \| \d+ \|', line)
        if m:
            k = m.group(1)
            lines[i] = f'| {k} | {stats_map[k]} |'

    # Update recent updates table: replace row if exists, otherwise insert below header separator
    case_date, scene = cols[1], cols[2]
    recent_line = f'| {case_date} | {case_id} | {scene} | {result} |'
    replaced = False
    for i, line in enumerate(lines):
        if f'| {case_id} |' in line and line.count('|') >= 5 and not line.startswith('| ' + case_id + ' |'):
            # avoid case table row; recent table row starts with date
            parts = split_row(line)
            if len(parts) == 4 and parts[1] == case_id:
                lines[i] = recent_line
                replaced = True
                break
    if not replaced:
        for i, line in enumerate(lines):
            if line.strip() == '|------|------|------|------|' and i > 0 and '最近更新' in '\n'.join(lines[max(0, i-5):i]):
                lines.insert(i+1, recent_line)
                break

    CASE_INDEX.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'old_result': old_result, 'new_result': result, 'scene': cols[2], 'date': cols[1]}


def update_scene_validation(scene: str, case_id: str, result: str):
    if result != '正反馈' or scene not in SCENE_LABELS or scene == 'other':
        return False
    text = SCENE_LIB.read_text(encoding='utf-8')
    lines = text.splitlines()
    changed = False
    for i, line in enumerate(lines):
        if line.startswith(f'| {scene} |'):
            cols = split_row(line)
            if len(cols) >= 6:
                case_ids = [] if cols[3] == '-' else [x.strip() for x in cols[3].split(',') if x.strip()]
                if case_id not in case_ids:
                    case_ids.append(case_id)
                count = len(case_ids)
                cols[2] = str(count)
                cols[3] = ', '.join(case_ids) if case_ids else '-'
                cols[4] = str(date.today())
                if count >= 3:
                    cols[1] = '已验证版'
                    cols[5] = '有效'
                else:
                    cols[1] = '理论版参考'
                    cols[5] = '待验证'
                lines[i] = build_row(cols)
                changed = True
            break
    if changed:
        SCENE_LIB.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return changed


def update_client(case_id: str, result: str, client: str | None, note: str = ''):
    if not CLIENTS.exists():
        return False
    data = json.loads(CLIENTS.read_text(encoding='utf-8'))
    names = [client] if client else [name for name, rec in data.items() if case_id in rec.get('case_ids', [])]
    changed = False
    for name in names:
        if not name or name not in data:
            continue
        rec = data[name]
        ids = rec.setdefault('case_ids', [])
        if case_id not in ids:
            ids.append(case_id)
        st = rec.setdefault('当前状态', {})
        if isinstance(st, dict):
            st['最近反馈'] = result
            st['最近反馈案例'] = case_id
            if note:
                st['最近反馈备注'] = note
            old_basis = st.get('依据', '')
            extra = f'反馈更新: {case_id}={result}'
            if extra not in old_basis:
                st['依据'] = (old_basis + '；' + extra).strip('；') if old_basis else extra
        rec['updated'] = str(date.today())
        changed = True
    if changed:
        CLIENTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('case_id')
    ap.add_argument('result', choices=sorted(VALID_RESULTS))
    ap.add_argument('--client', default=None)
    ap.add_argument('--note', default='')
    ap.add_argument('--dry-run', action='store_true', help='只预演，不写入文件')
    args = ap.parse_args()

    if args.dry_run:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            global CASE_INDEX, SCENE_LIB, CLIENTS
            orig_case, orig_scene, orig_clients = CASE_INDEX, SCENE_LIB, CLIENTS
            CASE_INDEX = tmp / '05-case-index.md'
            SCENE_LIB = tmp / '12-scene-reply-library.md'
            CLIENTS = tmp / 'clients.json'
            shutil.copy2(orig_case, CASE_INDEX)
            shutil.copy2(orig_scene, SCENE_LIB)
            shutil.copy2(orig_clients, CLIENTS)
            info = update_case_index(args.case_id, args.result, args.note)
            scene_changed = update_scene_validation(info['scene'], args.case_id, args.result)
            client_changed = update_client(args.case_id, args.result, args.client, args.note)
        print('DRY RUN：预演完成，未写入真实文件')
    else:
        info = update_case_index(args.case_id, args.result, args.note)
        scene_changed = update_scene_validation(info['scene'], args.case_id, args.result)
        client_changed = update_client(args.case_id, args.result, args.client, args.note)

    print('反馈更新完成' if not args.dry_run else '反馈更新预演完成')
    print(f"case_id: {args.case_id}")
    print(f"result: {info['old_result']} -> {info['new_result']}")
    print(f"scene: {info['scene']}")
    print(f"scene_validation_updated: {scene_changed}")
    print(f"client_updated: {client_changed}")
    print('注意：未修改 raw 原始聊天文件')

if __name__ == '__main__':
    main()
