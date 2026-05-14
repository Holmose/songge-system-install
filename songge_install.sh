#!/bin/sh
# 松哥撩妹系统 V2 安装脚本
#
# 使用方式：
# 1. 把 songge_install.sh 和 songge_system_v2_backup_encrypted.bin 放到同一目录
# 2. 运行: bash songge_install.sh
# 3. 输入密码完成安装
#
# 密码请联系松哥获取

echo "=========================================="
echo "松哥撩妹系统 V2 安装脚本"
echo "=========================================="
echo ""
echo "请确保以下文件在同一目录："
echo "  - songge_install.sh（本文件）"
echo "  - songge_system_v2_backup_encrypted.bin"
echo ""
echo "请输入解压密码："
read -r password

echo ""
echo "正在解密并安装..."

cd "$(dirname "$0")"

if [ ! -f "songge_system_v2_backup_encrypted.bin" ]; then
    echo ""
    echo "❌ 错误：找不到加密备份包"
    echo "请联系松哥获取下载链接"
    exit 1
fi

python3 << 'PYEOF'
import sys, base64, tarfile, os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

password = sys.argv[1] if len(sys.argv) > 1 else input("密码: ")
encrypted_file = "songge_system_v2_backup_encrypted.bin"

salt = b'songge_sync_salt_v1'
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
f = Fernet(key)

with open(encrypted_file, 'rb') as fin:
    encrypted = fin.read()

try:
    decrypted = f.decrypt(encrypted)
    print("✅ 解密成功")
except:
    print("❌ 解密失败！密码可能不对")
    print("请联系松哥获取最新密码")
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
    echo "验证：ls /var/minis/skills/ | grep songge"
else
    echo "❌ 安装失败"
fi
