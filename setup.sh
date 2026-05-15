#!/bin/sh
# System Setup Script v0.3
# 注意：只更新系统文件，学员个人信息保留本地

set -e

echo "=========================================="
echo "System Installer v0.3"
echo "=========================================="
echo ""

if [ ! -d "/var/minis" ]; then
    echo "⚠️  This script requires Minis iOS App environment"
    exit 1
fi

echo "Enter access code:"
read -r password

if [ -z "$password" ]; then
    echo "Error: Access code required"
    exit 1
fi

echo ""
echo "Downloading package..."

DOWNLOAD_URL="https://github.com/Holmose/songge-system-install/releases/download/v20260516/_pkg.bin"
BACKUP_FILE="/var/minis/workspace/_pkg.bin"

curl -L -o "$BACKUP_FILE" "$DOWNLOAD_URL" --progress-bar 2>/dev/null || {
    echo "Download failed"
    exit 1
}

echo ""
echo "Processing..."

python3 << 'PYEOF'
import sys, base64, tarfile, os, shutil, re
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
    print("✅ Decryption successful")
except:
    print("❌ Access code invalid")
    print("Please contact support for correct code")
    try:
        os.remove(encrypted_file)
    except:
        pass
    sys.exit(1)

temp_tar = '/var/minis/workspace/_tmp_pkg.tar.gz'
with open(temp_tar, 'wb') as fout:
    fout.write(decrypted)

print("Extracting system files...")

# 创建临时目录
temp_dir = '/var/minis/workspace/_temp_extract'
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir, exist_ok=True)

# 解压
with tarfile.open(temp_tar, 'r:gz') as tar:
    tar.extractall(temp_dir)

print("Updating system files...")

# 1. 更新skills（只覆盖songge开头的目录）
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
                print("  Updated: skills/" + item)
            elif item.endswith('.md') or item.endswith('.json'):
                shutil.copy2(src_item, dest_item)
                print("  Updated: skills/" + item)

# 2. 更新memory/songge/knowledge（系统知识）
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
            print("  Updated: knowledge/" + item)
        else:
            shutil.copy2(src_item, dest_item)
            print("  Updated: knowledge/" + item)

# 3. 更新05-case-index.md
idx_src = os.path.join(temp_dir, 'memory', 'songge', '05-case-index.md')
idx_dest = '/var/minis/memory/songge/05-case-index.md'
if os.path.exists(idx_src):
    shutil.copy2(idx_src, idx_dest)
    print(f"  Updated: 05-case-index.md")

# 4. 智能合并 GLOBAL.md（保留学员用户档案）
global_src = os.path.join(temp_dir, 'memory', 'GLOBAL.md')
global_dest = '/var/minis/memory/GLOBAL.md'

if os.path.exists(global_src):
    with open(global_src, 'r', encoding='utf-8') as f:
        new_global = f.read()
    
    # 检查本地是否有用户档案部分
    if os.path.exists(global_dest):
        with open(global_dest, 'r', encoding='utf-8') as f:
            local_global = f.read()
        
        # 智能合并策略：
        # 1. 搜索本地GLOBAL.md中的用户档案部分（## 用户档案）
        # 2. 如果有，保留本地用户档案，替换到新GLOBAL.md中
        # 3. 如果没有，直接使用新GLOBAL.md
        
        # 查找用户档案部分（多种模式匹配）
        user_profile_patterns = [
            '## 用户档案',
            '## 用户档案（',  # 如 ## 用户档案（Holmose）
            '## 用户profile',
            '## User Profile',
            '## 用户信息',
        ]
        
        local_user_profile = None
        for pattern in user_profile_patterns:
            idx = local_global.find(pattern)
            if idx != -1:
                local_user_profile = local_global[idx:]
                break
        
        if local_user_profile:
            # 提取新GLOBAL.md的用户档案部分之前的内容
            # 查找第一个用户档案标记的位置
            first_profile_idx = len(new_global)
            for pattern in user_profile_patterns:
                idx = new_global.find(pattern)
                if idx != -1 and idx < first_profile_idx:
                    first_profile_idx = idx
            
            # 保留新GLOBAL.md的系统规则部分
            system_rules = new_global[:first_profile_idx].strip()
            
            # 合并：系统规则 + 本地用户档案
            merged_global = system_rules + '\n\n' + local_user_profile
            
            with open(global_dest, 'w', encoding='utf-8') as f:
                f.write(merged_global)
            
            print("  Merged: GLOBAL.md (preserved user profile)")
        else:
            # 没有找到用户档案，直接使用新的
            shutil.copy2(global_src, global_dest)
            print("  Updated: GLOBAL.md (no user profile found)")
    else:
        # 本地没有GLOBAL.md，直接使用新的
        shutil.copy2(global_src, global_dest)
        print("  Created: GLOBAL.md")
else:
    print("  Skipped: GLOBAL.md not in package")

# 清理临时文件
shutil.rmtree(temp_dir, ignore_errors=True)
os.remove(temp_tar)
os.remove(encrypted_file)

print("✅ Installation complete!")
print("")
print("✅ 学员个人信息已保留")
print("✅ 系统规则已更新")
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Done!"
    echo "=========================================="
    echo ""
    echo "ℹ️  学员个人信息已保留"
    echo "ℹ️  系统规则已更新"
else
    echo "❌ Installation failed"
fi
