#!/bin/sh
# System Setup Script v0.1
#
# Usage:
#   curl -L https://github.com/Holmose/songge-system-install/raw/main/setup.sh -o setup.sh
#   bash setup.sh

set -e

echo "=========================================="
echo "System Installer v0.1"
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

# 更新下载链接
DOWNLOAD_URL="https://github.com/Holmose/songge-system-install/releases/download/v0.1-stable/_pkg.bin"
BACKUP_FILE="/var/minis/workspace/_pkg.bin"

curl -L -o "$BACKUP_FILE" "$DOWNLOAD_URL" --progress-bar 2>/dev/null || {
    echo "Download failed"
    exit 1
}

echo ""
echo "Processing..."

python3 << 'PYEOF'
import sys, base64, tarfile, os
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
    os.remove(encrypted_file)
    sys.exit(1)

temp_tar = '/var/minis/workspace/_tmp_pkg.tar.gz'
with open(temp_tar, 'wb') as fout:
    fout.write(decrypted)

print("Extracting...")
with tarfile.open(temp_tar, 'r:gz') as tar:
    tar.extractall('/var/minis/')

os.remove(temp_tar)
os.remove(encrypted_file)
print("✅ Installation complete!")
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Done!"
    echo "=========================================="
else
    echo "❌ Installation failed"
fi