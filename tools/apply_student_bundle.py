#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("用法: python3 apply_student_bundle.py /path/to/student_bundle_xxx.json")
    sys.exit(1)

bundle_path = Path(sys.argv[1])
if not bundle_path.exists():
    print("包不存在")
    sys.exit(1)

bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

# 写入文件
Path('/var/minis/skills/songge/tools').mkdir(parents=True, exist_ok=True)
Path('/var/minis/skills/songge/data').mkdir(parents=True, exist_ok=True)

Path('/var/minis/skills/songge/tools/songge_license_guard.py').write_text(bundle['files']['songge_license_guard.py'], encoding='utf-8')
Path('/var/minis/skills/songge/tools/license_expiry_reminder.py').write_text(bundle['files']['license_expiry_reminder.py'], encoding='utf-8')
Path('/var/minis/skills/songge/data/license_policy.json').write_text(json.dumps(bundle['policy'], ensure_ascii=False, indent=2), encoding='utf-8')
Path('/var/minis/skills/songge/data/license.json').write_text(json.dumps(bundle['license'], ensure_ascii=False, indent=2), encoding='utf-8')
if 'license_pubkey.pem' in bundle.get('files', {}):
    Path('/var/minis/skills/songge/data/license_pubkey.pem').write_text(bundle['files']['license_pubkey.pem'], encoding='utf-8')

print('更新包已应用')
print('请执行: python3 /var/minis/skills/songge/tools/songge_license_guard.py check')
