#!/usr/bin/env python3
import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_POLICY = "/var/minis/skills/songge/data/license_policy.json"


def _run(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return out
    except Exception:
        return ""


def get_device_fingerprint_raw():
    # 仅使用稳定字段，避免重启导致指纹漂移
    parts = []
    parts.append(platform.system())
    parts.append(platform.machine())
    parts.append(_run(["cat", "/etc/machine-id"]))
    parts.append(_run(["uname", "-s"]))
    parts.append(_run(["uname", "-m"]))
    # 可选盐，提高跨环境碰撞成本（不输出值）
    parts.append(os.environ.get("SONGGE_DEVICE_SALT", ""))
    return "|".join(parts)


def get_device_hash():
    raw = get_device_fingerprint_raw().encode()
    return hashlib.sha256(raw).hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_hmac(payload: dict, signature_b64: str, secret: str) -> bool:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    mac = hmac.new(secret.encode(), canonical, hashlib.sha256).digest()
    got = base64.b64decode(signature_b64.encode())
    return hmac.compare_digest(mac, got)


def check(policy_path):
    policy = load_json(policy_path)
    deny = policy.get("deny_message", "授权校验失败，拒绝输出")
    mode = policy.get("mode", "student_enforced")
    dev_hash = get_device_hash()

    if dev_hash in policy.get("master_devices", []):
        return {"status": "PASS_MASTER", "device_hash": dev_hash}

    if mode == "master_only":
        return {"status": "FAIL", "reason": "not_master", "message": deny}

    lic_path = policy.get("license_path")
    if not lic_path or not os.path.exists(lic_path):
        return {"status": "FAIL", "reason": "license_missing", "message": deny}

    lic = load_json(lic_path)
    required = ["student_id", "device_hash", "issued_at", "expires_at", "signature", "payload"]
    for k in required:
        if k not in lic:
            return {"status": "FAIL", "reason": f"license_field_missing:{k}", "message": deny}

    payload = lic.get("payload")
    if not isinstance(payload, dict):
        return {"status": "FAIL", "reason": "payload_invalid", "message": deny}

    # 字段一致性校验，防止外层字段与payload不一致
    for k in ["student_id", "device_hash", "issued_at", "expires_at"]:
        if str(lic.get(k)) != str(payload.get(k)):
            return {"status": "FAIL", "reason": f"payload_mismatch:{k}", "message": deny}

    if lic["device_hash"] != dev_hash:
        return {"status": "FAIL", "reason": "device_mismatch", "message": deny}

    now = int(time.time())
    if now > int(lic["expires_at"]):
        return {"status": "FAIL", "reason": "license_expired", "message": deny}

    secret = os.environ.get("SONGGE_LICENSE_SECRET", "")
    if not secret:
        return {"status": "FAIL", "reason": "secret_missing", "message": "缺少环境变量 SONGGE_LICENSE_SECRET"}

    ok = verify_hmac(payload, lic["signature"], secret)
    if not ok:
        return {"status": "FAIL", "reason": "signature_invalid", "message": deny}

    return {"status": "PASS_LICENSE", "device_hash": dev_hash, "student_id": lic.get("student_id")}


def issue(policy_path, student_id, days):
    policy = load_json(policy_path)
    dev_hash = get_device_hash()
    secret = os.environ.get("SONGGE_LICENSE_SECRET", "")
    if not secret:
        raise SystemExit("缺少环境变量 SONGGE_LICENSE_SECRET")

    now = int(time.time())
    expires = now + days * 86400
    payload = {
        "student_id": student_id,
        "device_hash": dev_hash,
        "issued_at": now,
        "expires_at": expires,
        "edition": "student"
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    sig = base64.b64encode(hmac.new(secret.encode(), canonical, hashlib.sha256).digest()).decode()
    license_obj = {
        "student_id": student_id,
        "device_hash": dev_hash,
        "issued_at": now,
        "expires_at": expires,
        "payload": payload,
        "signature": sig
    }
    out = policy.get("license_path", "/var/minis/skills/songge/data/license.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(license_obj, f, ensure_ascii=False, indent=2)
    return {"status": "ISSUED", "license_path": out, "device_hash": dev_hash, "student_id": student_id, "expires_at": expires}


def main():
    p = argparse.ArgumentParser(description="Songge device binding guard")
    p.add_argument("action", choices=["device", "check", "issue"])
    p.add_argument("--policy", default=DEFAULT_POLICY)
    p.add_argument("--student-id", default="student")
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()

    if args.action == "device":
        print(json.dumps({"device_hash": get_device_hash()}, ensure_ascii=False))
        return
    if args.action == "check":
        print(json.dumps(check(args.policy), ensure_ascii=False))
        return
    if args.action == "issue":
        print(json.dumps(issue(args.policy, args.student_id, args.days), ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
