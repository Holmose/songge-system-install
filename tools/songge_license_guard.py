#!/usr/bin/env python3
import argparse
import base64
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_POLICY = "/var/minis/skills/songge/data/license_policy.json"


def _run(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def get_device_fingerprint_raw():
    parts = [
        platform.system(),
        platform.machine(),
        _run(["cat", "/etc/machine-id"]),
        _run(["uname", "-s"]),
        _run(["uname", "-m"]),
        os.environ.get("SONGGE_DEVICE_SALT", "")
    ]
    return "|".join(parts)


def get_device_hash():
    return hashlib.sha256(get_device_fingerprint_raw().encode()).hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def canonical_payload(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sign_with_private_key(payload: dict, private_key_path: str) -> str:
    data = canonical_payload(payload)
    with tempfile.NamedTemporaryFile(delete=False) as f_data, tempfile.NamedTemporaryFile(delete=False) as f_sig:
        f_data.write(data)
        f_data.flush()
        cmd = ["openssl", "dgst", "-sha256", "-sign", private_key_path, "-out", f_sig.name, f_data.name]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sig = Path(f_sig.name).read_bytes()
    Path(f_data.name).unlink(missing_ok=True)
    Path(f_sig.name).unlink(missing_ok=True)
    return base64.b64encode(sig).decode()


def verify_with_public_key(payload: dict, signature_b64: str, public_key_path: str) -> bool:
    try:
        data = canonical_payload(payload)
        sig = base64.b64decode(signature_b64.encode())
        with tempfile.NamedTemporaryFile(delete=False) as f_data, tempfile.NamedTemporaryFile(delete=False) as f_sig:
            f_data.write(data)
            f_data.flush()
            Path(f_sig.name).write_bytes(sig)
            cmd = ["openssl", "dgst", "-sha256", "-verify", public_key_path, "-signature", f_sig.name, f_data.name]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Path(f_data.name).unlink(missing_ok=True)
        Path(f_sig.name).unlink(missing_ok=True)
        return True
    except Exception:
        return False


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
    pub_path = policy.get("public_key_path")
    if not lic_path or not os.path.exists(lic_path):
        return {"status": "FAIL", "reason": "license_missing", "message": deny}
    if not pub_path or not os.path.exists(pub_path):
        return {"status": "FAIL", "reason": "public_key_missing", "message": deny}

    lic = load_json(lic_path)
    required = ["student_id", "device_hash", "issued_at", "expires_at", "signature", "payload"]
    for k in required:
        if k not in lic:
            return {"status": "FAIL", "reason": f"license_field_missing:{k}", "message": deny}

    payload = lic.get("payload")
    if not isinstance(payload, dict):
        return {"status": "FAIL", "reason": "payload_invalid", "message": deny}
    for k in ["student_id", "device_hash", "issued_at", "expires_at"]:
        if str(lic.get(k)) != str(payload.get(k)):
            return {"status": "FAIL", "reason": f"payload_mismatch:{k}", "message": deny}

    if lic["device_hash"] != dev_hash:
        return {"status": "FAIL", "reason": "device_mismatch", "message": deny}
    if int(time.time()) > int(lic["expires_at"]):
        return {"status": "FAIL", "reason": "license_expired", "message": deny}
    if not verify_with_public_key(payload, lic["signature"], pub_path):
        return {"status": "FAIL", "reason": "signature_invalid", "message": deny}

    return {"status": "PASS_LICENSE", "device_hash": dev_hash, "student_id": lic.get("student_id")}


def issue(policy_path, student_id, days, device_hash=None):
    policy = load_json(policy_path)
    dev_hash = device_hash or get_device_hash()
    private_key_path = os.environ.get("SONGGE_LICENSE_PRIVATE_KEY_PATH", "")
    if not private_key_path or not os.path.exists(private_key_path):
        raise SystemExit("缺少或找不到私钥：SONGGE_LICENSE_PRIVATE_KEY_PATH")

    now = int(time.time())
    expires = now + int(days) * 86400
    payload = {
        "student_id": student_id,
        "device_hash": dev_hash,
        "issued_at": now,
        "expires_at": expires,
        "edition": "student"
    }
    sig = sign_with_private_key(payload, private_key_path)
    lic = {"student_id": student_id, "device_hash": dev_hash, "issued_at": now, "expires_at": expires, "payload": payload, "signature": sig}

    out = policy.get("license_path", "/var/minis/skills/songge/data/license.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(lic, f, ensure_ascii=False, indent=2)
    return {"status": "ISSUED", "license_path": out, "device_hash": dev_hash, "student_id": student_id, "expires_at": expires}


def main():
    p = argparse.ArgumentParser(description="Songge device binding guard")
    p.add_argument("action", choices=["device", "check", "issue"])
    p.add_argument("--policy", default=DEFAULT_POLICY)
    p.add_argument("--student-id", default="student")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--device-hash", default="")
    a = p.parse_args()

    if a.action == "device":
        print(json.dumps({"device_hash": get_device_hash()}, ensure_ascii=False)); return
    if a.action == "check":
        print(json.dumps(check(a.policy), ensure_ascii=False)); return
    if a.action == "issue":
        print(json.dumps(issue(a.policy, a.student_id, a.days, a.device_hash or None), ensure_ascii=False)); return


if __name__ == "__main__":
    main()
