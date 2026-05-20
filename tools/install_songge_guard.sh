#!/bin/sh
# Songge 学员端快速更新脚本（远程一键执行）
# 用法：
#   sh install_songge_guard.sh <BUNDLE_URL>
# 示例：
#   sh install_songge_guard.sh https://raw.githubusercontent.com/xxx/repo/main/student_bundle_abc.json

set -e

if [ "$#" -lt 1 ]; then
  echo "用法: sh install_songge_guard.sh <BUNDLE_URL>"
  exit 1
fi

BUNDLE_URL="$1"
TMP_BUNDLE="/tmp/songge_student_bundle.json"
APPLY_SCRIPT="/tmp/apply_student_bundle.py"

echo "[1/4] 下载更新包..."
curl -fsSL "$BUNDLE_URL" -o "$TMP_BUNDLE"

echo "[2/4] 下载应用脚本..."
# 内置应用脚本（避免依赖本地已有文件）
cat > "$APPLY_SCRIPT" << 'PY'
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("用法: python3 apply_student_bundle.py /path/to/student_bundle.json")
    sys.exit(1)

bundle_path = Path(sys.argv[1])
if not bundle_path.exists():
    print("包不存在")
    sys.exit(1)

bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

Path('/var/minis/skills/songge/tools').mkdir(parents=True, exist_ok=True)
Path('/var/minis/skills/songge/data').mkdir(parents=True, exist_ok=True)

Path('/var/minis/skills/songge/tools/songge_license_guard.py').write_text(bundle['files']['songge_license_guard.py'], encoding='utf-8')
Path('/var/minis/skills/songge/tools/license_expiry_reminder.py').write_text(bundle['files']['license_expiry_reminder.py'], encoding='utf-8')
Path('/var/minis/skills/songge/data/license_policy.json').write_text(json.dumps(bundle['policy'], ensure_ascii=False, indent=2), encoding='utf-8')
Path('/var/minis/skills/songge/data/license.json').write_text(json.dumps(bundle['license'], ensure_ascii=False, indent=2), encoding='utf-8')

print('更新包已应用')
PY

chmod +x "$APPLY_SCRIPT"

echo "[3/4] 应用更新包..."
python3 "$APPLY_SCRIPT" "$TMP_BUNDLE"

echo "[4/4] 验证授权状态..."
python3 /var/minis/skills/songge/tools/songge_license_guard.py check || true

echo "完成。"
