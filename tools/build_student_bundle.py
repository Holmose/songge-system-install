#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from pathlib import Path

TOOL = "/var/minis/skills/songge/tools/songge_license_guard.py"
OUT_DIR = Path("/var/minis/shared/songge/releases")


def run(cmd):
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", errors="ignore").strip()


def main():
    if len(sys.argv) < 4:
        print("用法: python3 build_student_bundle.py 学员ID 学员device_hash 天数")
        sys.exit(1)
    student_id = sys.argv[1]
    device_hash = sys.argv[2]
    days = sys.argv[3]

    # 为学员设备签发license（不是当前主控机）
    run(["python3", TOOL, "issue", "--student-id", student_id, "--device-hash", device_hash, "--days", days])

    lic_path = Path("/var/minis/skills/songge/data/license.json")
    pol_path = Path("/var/minis/skills/songge/data/license_policy.json")
    guard_path = Path(TOOL)
    rem_path = Path("/var/minis/skills/songge/tools/license_expiry_reminder.py")

    license_obj = json.loads(lic_path.read_text(encoding="utf-8"))
    policy = json.loads(pol_path.read_text(encoding="utf-8"))

    bundle = {
        "version": "songge-binding-v3-asymmetric",
        "generated_at": int(time.time()),
        "student_id": student_id,
        "policy": {
            "mode": policy.get("mode", "student_enforced"),
            "license_path": "/var/minis/skills/songge/data/license.json",
            "public_key_path": policy.get("public_key_path", "/var/minis/skills/songge/data/license_pubkey.pem"),
            "deny_message": policy.get("deny_message")
        },
        "license": license_obj,
        "files": {
            "songge_license_guard.py": guard_path.read_text(encoding="utf-8"),
            "license_expiry_reminder.py": rem_path.read_text(encoding="utf-8")
        }
    }

    # 打包公钥，学员端仅验签
    pub_path = Path(policy.get("public_key_path", "/var/minis/skills/songge/data/license_pubkey.pem"))
    if pub_path.exists():
        bundle["files"]["license_pubkey.pem"] = pub_path.read_text(encoding="utf-8")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"student_bundle_{student_id}.json"
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "bundle": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
