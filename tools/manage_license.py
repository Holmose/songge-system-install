#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path('/var/minis/skills/songge')
DB = ROOT / 'data' / 'student_licenses.json'
GUARD = ROOT / 'tools' / 'songge_license_guard.py'
BUILD = ROOT / 'tools' / 'build_student_bundle.py'
RELEASE_DIR = Path('/var/minis/shared/songge/releases')


def now_ts():
    return int(time.time())


def load_db():
    if not DB.exists():
        return {"students": []}
    return json.loads(DB.read_text(encoding='utf-8'))


def save_db(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def upsert_student(student_id, device_hash, expires_at, status='active'):
    data = load_db()
    arr = data.get('students', [])
    found = False
    for s in arr:
        if s.get('student_id') == student_id:
            s.update({'device_hash': device_hash, 'expires_at': int(expires_at), 'status': status, 'updated_at': now_ts()})
            found = True
            break
    if not found:
        arr.append({'student_id': student_id, 'device_hash': device_hash, 'expires_at': int(expires_at), 'status': status, 'created_at': now_ts(), 'updated_at': now_ts()})
    data['students'] = arr
    save_db(data)


def issue(student_id, device_hash, days):
    cmd = ['python3', str(GUARD), 'issue', '--student-id', student_id, '--device-hash', device_hash, '--days', str(days)]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore').strip()
    obj = json.loads(out)
    upsert_student(student_id, device_hash, obj['expires_at'], status='active')
    print(json.dumps({'status': 'ok', 'action': 'issue', 'student_id': student_id, 'device_hash': device_hash, 'expires_at': obj['expires_at']}, ensure_ascii=False))


def build_bundle(student_id, device_hash, days):
    cmd = ['python3', str(BUILD), student_id, device_hash, str(days)]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore').strip()
    obj = json.loads(out)
    print(json.dumps({'status': 'ok', 'action': 'build', 'bundle': obj.get('bundle'), 'student_id': student_id}, ensure_ascii=False))


def issue_and_build(student_id, device_hash, days):
    issue(student_id, device_hash, days)
    build_bundle(student_id, device_hash, days)


def export_install_cmd(student_id, provider='github'):
    if provider == 'github':
        install_url = 'https://raw.githubusercontent.com/Holmose/songge-system-install/master/install_songge_guard.sh'
        bundle_url = f'https://raw.githubusercontent.com/Holmose/songge-system-install/master/student_bundle_{student_id}.json'
    else:
        install_url = 'https://gitee.com/holmose/songge-system-install/raw/master/install_songge_guard.sh'
        bundle_url = f'https://gitee.com/holmose/songge-system-install/raw/master/student_bundle_{student_id}.json'
    cmd = f'curl -fsSL "{install_url}" -o /tmp/install_songge_guard.sh && sh /tmp/install_songge_guard.sh "{bundle_url}"'
    print(json.dumps({'student_id': student_id, 'provider': provider, 'install_command': cmd}, ensure_ascii=False, indent=2))


def list_students(show_all=False):
    data = load_db(); arr = data.get('students', []); now = now_ts(); rows = []
    for s in arr:
        left_days = int((int(s.get('expires_at', 0)) - now) // 86400)
        row = dict(s); row['left_days'] = left_days
        if show_all or s.get('status') != 'revoked': rows.append(row)
    print(json.dumps({'students': rows, 'count': len(rows)}, ensure_ascii=False, indent=2))


def renew(student_id, days):
    data = load_db()
    for s in data.get('students', []):
        if s.get('student_id') == student_id:
            return issue(student_id, s.get('device_hash'), days)
    raise SystemExit('未找到学员，请先 issue')


def revoke(student_id):
    data = load_db(); found = False
    for s in data.get('students', []):
        if s.get('student_id') == student_id:
            s['status'] = 'revoked'; s['updated_at'] = now_ts(); found = True; break
    if not found: raise SystemExit('未找到学员')
    save_db(data)
    print(json.dumps({'status': 'ok', 'action': 'revoke', 'student_id': student_id}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description='Songge license manager')
    sub = p.add_subparsers(dest='cmd', required=True)
    p_issue = sub.add_parser('issue'); p_issue.add_argument('--student-id', required=True); p_issue.add_argument('--device-hash', required=True); p_issue.add_argument('--days', type=int, default=30)
    p_ib = sub.add_parser('issue-build'); p_ib.add_argument('--student-id', required=True); p_ib.add_argument('--device-hash', required=True); p_ib.add_argument('--days', type=int, default=30)
    p_build = sub.add_parser('build'); p_build.add_argument('--student-id', required=True); p_build.add_argument('--device-hash', required=True); p_build.add_argument('--days', type=int, default=30)
    p_cmd = sub.add_parser('export-install-cmd'); p_cmd.add_argument('--student-id', required=True); p_cmd.add_argument('--provider', choices=['github','gitee'], default='github')
    p_list = sub.add_parser('list'); p_list.add_argument('--all', action='store_true')
    p_renew = sub.add_parser('renew'); p_renew.add_argument('--student-id', required=True); p_renew.add_argument('--days', type=int, default=30)
    p_revoke = sub.add_parser('revoke'); p_revoke.add_argument('--student-id', required=True)

    a = p.parse_args()
    if a.cmd == 'issue': issue(a.student_id, a.device_hash, a.days)
    elif a.cmd == 'issue-build': issue_and_build(a.student_id, a.device_hash, a.days)
    elif a.cmd == 'build': build_bundle(a.student_id, a.device_hash, a.days)
    elif a.cmd == 'export-install-cmd': export_install_cmd(a.student_id, a.provider)
    elif a.cmd == 'list': list_students(a.all)
    elif a.cmd == 'renew': renew(a.student_id, a.days)
    elif a.cmd == 'revoke': revoke(a.student_id)


if __name__ == '__main__':
    main()
