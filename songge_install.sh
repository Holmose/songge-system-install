#!/bin/sh
# 松哥撩妹系统 V2 自动安装脚本
#
# 一条命令搞定全部安装：
# curl -s https://raw.githubusercontent.com/Holmose/songge-system-install/main/songge_install.sh | bash
#
# 或者保存后运行：
# bash songge_install.sh

set -e

echo "=========================================="
echo "松哥撩妹系统 V2 自动安装"
echo "=========================================="
echo ""

# 检测运行环境
if [ ! -d "/var/minis" ]; then
    echo "❌ 此脚本需要在 Minis iOS App 中运行"
    exit 1
fi

# 获取密码
echo "请输入解压密码："
read -r password

if [ -z "$password" ]; then
    echo "❌ 密码不能为空"
    exit 1
fi

echo ""
echo "正在下载加密包..."

# 下载地址（从GitHub Release）
DOWNLOAD_URL="https://github.com/Holmose/songge-system-install/releases/download/v2.0/songge_system_v2_backup_encrypted.bin"
BACKUP_FILE="/var/minis/workspace/songge_system_v2_backup_encrypted.bin"

# 下载
curl -L -o "$BACKUP_FILE" "$DOWNLOAD_URL" --progress-bar

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 下载失败"
    exit 1
fi

echo ""
echo "✅ 下载完成，正在解密..."

# 解密并解压
python3 << PYEOF
import sys, base64, tarfile, os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = "$password"
encrypted_file = "/var/minis/workspace/songge_system_v2_backup_encrypted.bin"

salt = b'songge_sync_salt_v1'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
f = Fernet(key)

try:
    with open(encrypted_file, 'rb') as fin:
        encrypted = fin.read()
    
    decrypted = f.decrypt(encrypted)
    print("✅ 解密成功")
except Exception as e:
    print("❌ 解密失败！密码可能不对")
    print("请确认密码是否正确，联系松哥获取最新密码")
    sys.exit(1)

temp_tar = '/var/minis/workspace/_temp_songge.tar.gz'
with open(temp_tar, 'wb') as fout:
    fout.write(decrypted)

print("正在解压...")
with tarfile.open(temp_tar, 'r:gz') as tar:
    tar.extractall('/var/minis/')

os.remove(temp_tar)
os.remove(encrypted_file)
print("✅ 安装完成！")
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 安装完成！"
    echo "=========================================="
    echo ""
    echo "验证安装："
    ls /var/minis/skills/ 2>/dev/null | grep songge || echo "（Skills目录验证）"
    echo ""
    echo "使用方式："
    echo "  分析聊天：说 '分析聊天' / '怎么回'"
    echo "  判断状态：说 '判断阶段' / '判断窗口'"
else
    echo "❌ 安装失败"
fi