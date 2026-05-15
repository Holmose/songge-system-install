#!/bin/sh
# System Setup Script v0.5 (Gitee)

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

DOWNLOAD_URL="https://gitee.com/holmose/songge-system-install/raw/master/_pkg.bin"
BACKUP_FILE="/var/minis/workspace/_pkg.bin"

curl -L -o "$BACKUP_FILE" "$DOWNLOAD_URL" --progress-bar 2>/dev/null || {
    echo "Download failed"
    exit 1
}

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
        encrypted = fin.read()
    decrypted = f.decrypt(encrypted)
    print("Decryption successful")
except:
    print("Access code invalid")
    try:
        os.remove(encrypted_file)
    except:
        pass
    sys.exit(1)

temp_tar = '/var/minis/workspace/_tmp_pkg.tar.gz'
with open(temp_tar, 'wb') as fout:
    fout.write(decrypted)

temp_dir = '/var/minis/workspace/_temp_extract'
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir, exist_ok=True)

with tarfile.open(temp_tar, 'r:gz') as tar:
    tar.extractall(temp_dir)

# 更新skills
skills_dest = '/var/minis/skills'
skills_src = os.path.join(temp_dir, 'skills')

if os.path.exists(skills_src):
    for item in os.listdir(skills_src):
        if item.startswith('songge'):
            src_item = os.path.join(skills_src, item)
            dest_item = os.path.join(skills_dest, item)
            if os.path.isdir(src_item):
                shutil.rmtree(dest_item, ignore_errors=True)
                shutil.copytree(src_item, dest_item)

# 更新knowledge
mem_dest = '/var/minis/memory/songge'
kn_src = os.path.join(temp_dir, 'memory', 'songge', 'knowledge')
kn_dest = os.path.join(mem_dest, 'knowledge')

if os.path.exists(kn_src):
    if os.path.exists(kn_dest):
        shutil.rmtree(kn_dest, ignore_errors=True)
    os.makedirs(kn_dest, exist_ok=True)
    for item in os.listdir(kn_src):
        src_item = os.path.join(kn_src, item)
        dest_item = os.path.join(kn_dest, item)
        if os.path.isdir(src_item):
            shutil.copytree(src_item, dest_item)
        else:
            shutil.copy2(src_item, dest_item)

# 智能合并GLOBAL.md
global_src = os.path.join(temp_dir, 'memory', 'GLOBAL.md')
global_dest = '/var/minis/memory/GLOBAL.md'

if os.path.exists(global_src):
    with open(global_src, 'r', encoding='utf-8') as f:
        new_global = f.read()
    
    if os.path.exists(global_dest):
        with open(global_dest, 'r', encoding='utf-8') as f:
            local_global = f.read()
        
        patterns = ['## 用户档案', '## 用户档案（', '## 用户profile', '## User Profile', '## 用户信息', '## 我的设定']
        
        local_user_profile = None
        for pattern in patterns:
            idx = local_global.find(pattern)
            if idx != -1:
                local_user_profile = local_global[idx:]
                break
        
        if local_user_profile:
            first_profile_idx = len(new_global)
            for pattern in patterns:
                idx = new_global.find(pattern)
                if idx != -1 and idx < first_profile_idx:
                    first_profile_idx = idx
            
            system_rules = new_global[:first_profile_idx].strip()
            merged = system_rules + '\n\n' + local_user_profile
            
            with open(global_dest, 'w', encoding='utf-8') as f:
                f.write(merged)
        else:
            shutil.copy2(global_src, global_dest)
    else:
        shutil.copy2(global_src, global_dest)

shutil.rmtree(temp_dir, ignore_errors=True)
os.remove(temp_tar)
os.remove(encrypted_file)

print("Installation complete!")
PYEOF
