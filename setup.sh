#!/bin/sh
# System Setup Script v0.5

set -e

echo "=========================================="
echo "System Installer v0.5"
echo "=========================================="
echo ""

if [ ! -d "/var/minis" ]; then
    echo "This script requires Minis iOS App"
    exit 1
fi

echo "Enter access code:"
read -r password

if [ -z "$password" ]; then
    echo "Password required"
    exit 1
fi

echo ""
echo "Downloading..."

curl -L -o "/var/minis/workspace/_pkg.bin" "https://gitee.com/holmose/songge-system-install/raw/master/_pkg.bin" --progress-bar 2>/dev/null

echo "Processing..."

python3 << 'PYEOF'
import sys, base64, tarfile, os, shutil
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = sys.argv[1] if len(sys.argv) > 1 else ""
encrypted_file = "/var/minis/workspace/_pkg.bin"

salt = b'songge_sync_salt_v1'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
f = Fernet(key)

try:
    with open(encrypted_file, 'rb') as fin:
        decrypted = f.decrypt(fin.read())
    print("Decryption successful")
except:
    print("Access code invalid")
    sys.exit(1)

with open('/var/minis/workspace/_tmp.tar.gz', 'wb') as fout:
    fout.write(decrypted)

temp_dir = '/var/minis/workspace/_temp'
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

with tarfile.open('/var/minis/workspace/_tmp.tar.gz', 'r:gz') as tar:
    tar.extractall(temp_dir)

# 更新skills
skills_dest = '/var/minis/skills'
skills_src = os.path.join(temp_dir, 'skills')
if os.path.exists(skills_src):
    for item in os.listdir(skills_src):
        if item.startswith('songge'):
            src = os.path.join(skills_src, item)
            dest = os.path.join(skills_dest, item)
            if os.path.isdir(src):
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(src, dest)

# 更新knowledge
mem_dest = '/var/minis/memory/songge'
kn_src = os.path.join(temp_dir, 'memory', 'songge', 'knowledge')
kn_dest = os.path.join(mem_dest, 'knowledge')
if os.path.exists(kn_src):
    if os.path.exists(kn_dest):
        shutil.rmtree(kn_dest, ignore_errors=True)
    os.makedirs(kn_dest, exist_ok=True)
    for item in os.listdir(kn_src):
        src = os.path.join(kn_src, item)
        dest = os.path.join(kn_dest, item)
        if os.path.isdir(src):
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)

# 智能合并GLOBAL.md
global_src = os.path.join(temp_dir, 'memory', 'GLOBAL.md')
global_dest = '/var/minis/memory/GLOBAL.md'
if os.path.exists(global_src):
    with open(global_src, 'r', encoding='utf-8') as f:
        new_global = f.read()
    if os.path.exists(global_dest):
        with open(global_dest, 'r', encoding='utf-8') as f:
            local = f.read()
        patterns = ['## 用户档案', '## 用户档案（', '## 用户profile', '## User Profile', '## 用户信息', '## 我的设定']
        local_profile = None
        for p in patterns:
            idx = local.find(p)
            if idx != -1:
                local_profile = local[idx:]
                break
        if local_profile:
            first_idx = len(new_global)
            for p in patterns:
                idx = new_global.find(p)
                if idx != -1 and idx < first_idx:
                    first_idx = idx
            merged = new_global[:first_idx].strip() + '

' + local_profile
            with open(global_dest, 'w', encoding='utf-8') as f:
                f.write(merged)
        else:
            shutil.copy2(global_src, global_dest)
    else:
        shutil.copy2(global_src, global_dest)

shutil.rmtree(temp_dir, ignore_errors=True)
os.remove('/var/minis/workspace/_tmp.tar.gz')
os.remove(encrypted_file)
print("Installation complete!")
PYEOF
