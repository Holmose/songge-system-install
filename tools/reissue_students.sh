#!/bin/sh
# 学员批量重签发（在每个学员设备本机执行）
# 前提：已设置 SONGGE_LICENSE_SECRET

set -e

ISSUE_TOOL="python3 /var/minis/skills/songge/tools/songge_license_guard.py issue"
CHECK_TOOL="python3 /var/minis/skills/songge/tools/songge_license_guard.py check"

# 用法：sh reissue_students.sh 学员名1 学员名2 ...
if [ "$#" -lt 1 ]; then
  echo "用法: sh reissue_students.sh 学员名1 学员名2 ..."
  exit 1
fi

for student in "$@"; do
  echo "== 重签发: $student =="
  $ISSUE_TOOL --student-id "$student" --days 30
  $CHECK_TOOL
  echo ""
done

echo "批量重签发完成。"
