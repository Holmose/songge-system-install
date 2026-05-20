#!/usr/bin/env python3
import json
import subprocess
import time
import sys

CHECK_CMD = ["python3", "/var/minis/skills/songge/tools/songge_license_guard.py", "check"]
THRESHOLD_DAYS = 7


def main():
    try:
        out = subprocess.check_output(CHECK_CMD, stderr=subprocess.STDOUT).decode("utf-8", errors="ignore").strip()
        data = json.loads(out)
    except Exception:
        print("[提醒] 授权检查失败：请联系管理员重绑。")
        return 2

    status = data.get("status", "")
    if status == "PASS_MASTER":
        print("[提醒] 当前为主控机白名单，无需到期提醒。")
        return 0

    if status != "PASS_LICENSE":
        print("[提醒] 授权未通过，请先完成绑定。")
        return 1

    # 从license文件读取到期时间
    try:
        with open("/var/minis/skills/songge/data/license.json", "r", encoding="utf-8") as f:
            lic = json.load(f)
        expires_at = int(lic.get("expires_at", 0))
    except Exception:
        print("[提醒] 无法读取授权到期信息，请联系管理员。")
        return 2

    now = int(time.time())
    left_sec = expires_at - now
    left_days = left_sec // 86400

    if left_sec <= 0:
        print("[提醒] 授权已过期，请立即续期。")
        return 1

    if left_days <= THRESHOLD_DAYS:
        print(f"[提醒] 授权将在 {left_days} 天内到期，请尽快续期。")
        return 1

    print(f"[提醒] 授权正常，剩余 {left_days} 天。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
