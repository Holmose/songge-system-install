#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path('/var/minis/skills/songge')
DB = ROOT / 'data' / 'student_licenses.json'
GUARD = ROOT / 'tools' / 'songge_license_guard.py'


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
            s.update({
                'device_hash': device_hash,
                'expires_at': int(expires_at),
                'status': status,
                'updated_at': now_ts()
            })
            found = True
            break
    if not found:
        arr.append({
            'student_id': student_id,
            'device_hash': device_hash,
            'expires_at': int(expires_at),
            'status': status,
            'created_at': now_ts(),
            'updated_at': now_ts()
        })
    data['students'] = arr
    save_db(data)


def issue(student_id, device_hash, days):
    cmd = [
        'python3', str(GUARD), 'issue',
        '--student-id', student_id,
        '--device-hash', device_hash,
        '--days', str(days)
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore').strip()
    obj = json.loads(out)
    upsert_student(student_id, device_hash, obj['expires_at'], status='active')
    print(json.dumps({
        'status': 'ok',
        'action': 'issue',
        'student_id': student_id,
        'device_hash': device_hash,
        'expires_at': obj['expires_at']
    }, ensure_ascii=False))


def list_students(show_all=False):
    data = load_db()
    arr = data.get('students', [])
    now = now_ts()
    rows = []
    for s in arr:
        left_days = int((int(s.get('expires_at', 0)) - now) // 86400)
        row = dict(s)
        row['left_days'] = left_days
        if show_all or s.get('status') != 'revoked':
            rows.append(row)
    print(json.dumps({'students': rows, 'count': len(rows)}, ensure_ascii=False, indent=2))


def renew(student_id, days):
    data = load_db()
    for s in data.get('students', []):
        if s.get('student_id') == student_id:
            return issue(student_id, s.get('device_hash'), days)
    raise SystemExit('未找到学员，请先 issue')


def revoke(student_id):
    data = load_db()
    found = False
    for s in data.get('students', []):
        if s.get('student_id') == student_id:
            s['status'] = 'revoked'
            s['updated_at'] = now_ts()
            found = True
            break
    if not found:
        raise SystemExit('未找到学员')
    save_db(data)
    print(json.dumps({'status': 'ok', 'action': 'revoke', 'student_id': student_id}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description='Songge license manager')
    sub = p.add_subparsers(dest='cmd', required=True)

    p_issue = sub.add_parser('issue')
    p_issue.add_argument('--student-id', required=True)
    p_issue.add_argument('--device-hash', required=True)
    p_issue.add_argument('--days', type=int, default=30)

    p_list = sub.add_parser('list')
    p_list.add_argument('--all', action='store_true')

    p_renew = sub.add_parser('renew')
    p_renew.add_argument('--student-id', required=True)
    p_renew.add_argument('--days', type=int, default=30)

    p_revoke = sub.add_parser('revoke')
    p_revoke.add_argument('--student-id', required=True)

    a = p.parse_args()
    if a.cmd == 'issue':
        issue(a.student_id, a.device_hash, a.days)
    elif a.cmd == 'list':
        list_students(a.all)
    elif a.cmd == 'renew':
        renew(a.student_id, a.days)
    elif a.cmd == 'revoke':
        revoke(a.student_id)


if __name__ == '__main__':
    main()
