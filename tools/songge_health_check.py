#!/usr/bin/env python3
"""
松哥系统健康检查脚本

检查内容：
1. 原始数据清单是否存在，raw/case/profile 文件哈希是否变化
2. case-index 是否有重复编号、统计是否同步
3. 客户主库 JSON 是否有效、字段是否完整
4. 是否存在明文密钥残留
5. songge 技能目录 Git 状态是否 clean
6. 话术库是否疑似存在未验证入库风险

只读检查，不修改任何业务文件。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT_SKILLS = Path('/var/minis/skills')
ROOT_MEMORY = Path('/var/minis/memory')
SONGGE = ROOT_SKILLS / 'songge'
CLIENTS = SONGGE / 'data/clients.json'
CASE_INDEX = ROOT_MEMORY / 'songge/05-case-index.md'
MANIFEST = ROOT_MEMORY / 'songge/raw-data-protection-manifest-2026-05-04.md'
SCENE_LIB = ROOT_MEMORY / 'songge/knowledge/12-scene-reply-library.md'

RAW_DIRS = [
    Path('/var/minis/skills/songge/data/chats_raw'),
    Path('/var/minis/skills/songge/data/clients_profile'),
    Path('/var/minis/memory/songge/case-logs'),
    Path('/var/minis/shared/songge/cases'),
]

SECRET_PATTERNS = [
    re.compile(r'b7db5413', re.I),
    re.compile(r'cxdKa8ZFmOjlFzXQ', re.I),
    re.compile(r'sk-[A-Za-z0-9_-]{20,}'),
]

SECRET_SCAN_EXCLUDE = {
    str(Path('/var/minis/skills/songge/tools/songge_health_check.py')),
}

class Report:
    def __init__(self):
        self.ok = []
        self.warn = []
        self.fail = []
    def add(self, level, msg):
        getattr(self, level).append(msg)
    def print(self):
        print('# 松哥系统健康检查')
        print()
        for title, items in [('FAIL', self.fail), ('WARN', self.warn), ('OK', self.ok)]:
            print(f'## {title} ({len(items)})')
            if not items:
                print('- 无')
            else:
                for x in items:
                    print(f'- {x}')
            print()
        return 1 if self.fail else 0

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def parse_manifest():
    entries = {}
    if not MANIFEST.exists():
        return entries
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        if not line.startswith('|') or '|' not in line:
            continue
        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) != 4 or cols[0] in ('类型', '------'):
            continue
        typ, size, sha, path = cols
        if path.startswith('/var/minis/') and sha and size.isdigit():
            entries[path] = {'type': typ, 'size': int(size), 'sha': sha}
    return entries

def check_raw_manifest(r: Report):
    entries = parse_manifest()
    if not entries:
        r.fail.append(f'原始数据保护清单不存在或不可解析：{MANIFEST}')
        return
    changed = []
    missing = []
    for path, meta in entries.items():
        p = Path(path)
        if not p.exists():
            missing.append(path)
            continue
        size = p.stat().st_size
        sha = sha256_file(p)
        if size != meta['size'] or sha != meta['sha']:
            changed.append(path)
    if missing:
        r.fail.append('原始数据清单中文件缺失：' + ', '.join(missing[:5]))
    if changed:
        r.fail.append('原始数据哈希/大小发生变化：' + ', '.join(changed[:5]))
    if not missing and not changed:
        r.ok.append(f'原始数据清单校验通过，共 {len(entries)} 个文件')
    # detect new raw-like files not in manifest
    known = set(entries)
    current = []
    for d in RAW_DIRS:
        if d.exists():
            current.extend(str(p) for p in sorted(d.iterdir()) if p.is_file())
    new_files = [p for p in current if p not in known]
    if new_files:
        r.warn.append('发现清单外新增 raw/case/profile 文件，建议更新 manifest：' + ', '.join(new_files[:5]))


def parse_case_rows():
    rows = []
    if not CASE_INDEX.exists():
        return rows
    for line in CASE_INDEX.read_text(encoding='utf-8').splitlines():
        if line.startswith('| 202'):
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) >= 11:
                rows.append(cols[:11])
    return rows

def parse_stats():
    stats = {}
    text = CASE_INDEX.read_text(encoding='utf-8') if CASE_INDEX.exists() else ''
    for line in text.splitlines():
        m = re.match(r'\| (总案例数|已发送-正反馈|已发送-普通反馈|已发送-冷淡|已发送-翻车|未发送|待反馈|待验证) \| (\d+) \|', line)
        if m:
            stats[m.group(1)] = int(m.group(2))
    return stats

def check_case_index(r: Report):
    if not CASE_INDEX.exists():
        r.fail.append(f'缺少 case-index：{CASE_INDEX}')
        return
    rows = parse_case_rows()
    ids = [x[0] for x in rows]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        r.fail.append('case-index 存在重复编号：' + ', '.join(dup))
    else:
        r.ok.append(f'case-index 编号无重复，共 {len(rows)} 条')
    stats = parse_stats()
    result_counts = Counter(x[9] for x in rows)
    expected = {
        '总案例数': len(rows),
        '已发送-正反馈': result_counts.get('正反馈', 0),
        '已发送-普通反馈': result_counts.get('普通反馈', 0),
        '已发送-冷淡': result_counts.get('冷淡', 0),
        '已发送-翻车': result_counts.get('翻车', 0),
        '未发送': result_counts.get('未发送', 0),
        '待反馈': result_counts.get('待反馈', 0),
        '待验证': result_counts.get('待验证', 0),
    }
    mismatch = {k: (stats.get(k), v) for k, v in expected.items() if stats.get(k) != v}
    if mismatch:
        r.warn.append('case-index 统计可能不同步：' + repr(mismatch))
    else:
        r.ok.append('case-index 统计区与案例表同步')

def check_clients(r: Report):
    if not CLIENTS.exists():
        r.fail.append(f'缺少客户主库：{CLIENTS}')
        return
    try:
        data = json.loads(CLIENTS.read_text(encoding='utf-8'))
    except Exception as e:
        r.fail.append(f'clients.json 不是有效 JSON：{e}')
        return
    required = ['当前状态', '微信备注', 'raw_chat_files', 'case_ids']
    missing = defaultdict(list)
    for name, rec in data.items():
        for k in required:
            if k not in rec:
                missing[k].append(name)
        st = rec.get('当前状态')
        if not isinstance(st, dict):
            missing['当前状态非dict'].append(name)
        else:
            for k in ['阶段', '配合度', '窗口', '风险', '推荐动作', '禁止动作', '推荐技能', '依据']:
                if k not in st:
                    missing[f'当前状态.{k}'].append(name)
    if missing:
        r.fail.append('客户主库字段缺失：' + '; '.join(f'{k}:{v}' for k, v in missing.items()))
    else:
        r.ok.append(f'客户主库结构完整，共 {len(data)} 人')
    # stale secondary client DB warning
    secondary = Path('/var/minis/skills/songge-wenzhong/data/clients.json')
    if secondary.exists():
        r.warn.append('存在历史客户副本 songge-wenzhong/data/clients.json；规则上只读主库，不应再更新副本')

def iter_text_files(base: Path):
    if not base.exists():
        return
    for p in base.rglob('*'):
        if not p.is_file():
            continue
        if any(part == '.git' for part in p.parts):
            continue
        if p.suffix.lower() in {'.md', '.py', '.json', '.txt', '.bak', '.yml', '.yaml'} or p.name == 'SKILL.md':
            yield p

def check_secrets(r: Report):
    hits = []
    for base in [ROOT_SKILLS, ROOT_MEMORY / 'songge']:
        for p in iter_text_files(base):
            if str(p) in SECRET_SCAN_EXCLUDE:
                continue
            try:
                txt = p.read_text(encoding='utf-8')
            except Exception:
                continue
            for pat in SECRET_PATTERNS:
                if pat.search(txt):
                    hits.append(str(p))
                    break
    if hits:
        r.fail.append('发现疑似明文密钥残留：' + ', '.join(sorted(set(hits))[:10]))
    else:
        r.ok.append('未发现已知明文密钥模式残留')

def check_git_status(r: Report):
    dirty = []
    no_git = []
    for d in sorted([p for p in ROOT_SKILLS.iterdir() if p.is_dir() and p.name.startswith('songge')]):
        if not (d / '.git').exists():
            no_git.append(d.name)
            continue
        try:
            out = subprocess.check_output(['git', '-C', str(d), 'status', '--short'], text=True)
        except Exception as e:
            dirty.append(f'{d.name}: git status failed {e}')
            continue
        if out.strip():
            dirty.append(f'{d.name}: {out.strip().replace(chr(10), "; ")}')
    if no_git:
        r.fail.append('存在无 Git 的 songge 目录：' + ', '.join(no_git))
    else:
        r.ok.append('所有 songge* 技能目录均已初始化 Git')
    if dirty:
        r.warn.append('存在未提交变更：' + ' | '.join(dirty[:10]))
    else:
        r.ok.append('所有 songge* Git 仓库状态 clean')

def check_scene_library(r: Report):
    if not SCENE_LIB.exists():
        r.warn.append('缺少场景话术库，跳过话术门禁检查')
        return
    txt = SCENE_LIB.read_text(encoding='utf-8')
    if '## 话术验证索引' not in txt:
        r.warn.append('话术库缺少“话术验证索引”；无法追踪 case_id 证据')
        return
    scene_count = len(re.findall(r'^## \d+\. ', txt, flags=re.M))
    quality_count = txt.count('| 质量等级 | 理论版参考 |') + txt.count('| 质量等级 | 已验证版 |') + txt.count('| 质量等级 | 失效 |')
    case_field_count = txt.count('| 正反馈 case_ids |')
    if scene_count < 15:
        r.warn.append(f'话术库场景数少于预期：{scene_count}/15')
    if quality_count < scene_count:
        r.warn.append(f'话术库沉淀状态缺质量等级字段：{quality_count}/{scene_count}')
    if case_field_count < scene_count:
        r.warn.append(f'话术库沉淀状态缺正反馈 case_ids 字段：{case_field_count}/{scene_count}')
    verified_lines = [line for line in txt.splitlines() if '| 已验证版 |' in line]
    bad_verified = [line for line in verified_lines if re.search(r'\| 已验证版 \| [0-2] \|', line) or '| - |' in line]
    if bad_verified:
        r.fail.append('话术库存在疑似未满3次或无case_id却标已验证版的条目')
    elif quality_count >= scene_count and case_field_count >= scene_count:
        r.ok.append(f'话术库门禁字段完整，场景数 {scene_count}；已验证版需人工确保绑定3次正反馈')

def main():
    r = Report()
    check_raw_manifest(r)
    check_case_index(r)
    check_clients(r)
    check_secrets(r)
    check_git_status(r)
    check_scene_library(r)
    code = r.print()
    return code

if __name__ == '__main__':
    raise SystemExit(main())
