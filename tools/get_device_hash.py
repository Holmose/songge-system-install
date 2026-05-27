#!/usr/bin/env python3
"""
松哥系统 - 设备机器码生成脚本
首次运行自动生成机器码，永久保存到本地
学员将机器码发给松哥完成激活

用法: python3 get_device_hash.py
"""

import hashlib
import platform
import os
import stat
import time

# ============================================================
# 系统级固定盐值 - 全球唯一标识松哥系统
# 勿改动，改动将导致所有已有机器码失效
# ============================================================
SYSTEM_SALT = "SONGGE_LICENSE_V1_2025"

# 本地机器码存储路径（放在脚本同目录下）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MACHINE_CODE_FILE = os.path.join(SCRIPT_DIR, ".machine_code")

# ============================================================
# 核心：设备指纹采集（不依赖 machine-id）
# ============================================================

def _safe_read(path, limit=1024):
    """安全读取文件前N字节，无则返回空"""
    try:
        with open(path, "rb") as f:
            return f.read(limit).decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _run(cmd_list):
    """安全执行命令，返回stdout.strip()"""
    import subprocess
    try:
        return subprocess.check_output(cmd_list, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""


def collect_device_fingerprint():
    """
    采集设备指纹，组成唯一标识字符串
    覆盖系统/架构/cpu/内存/进程/容器等维度
    """
    parts = []

    # 1. 系统基础信息
    parts.append(platform.system())          # Linux / Darwin
    parts.append(platform.machine())         # aarch64 / x86_64
    parts.append(platform.version())         # 内核版本
    parts.append(platform.processor())        # 处理器名

    # 2. CPU信息（取前500字节做哈希）
    cpu_raw = _safe_read("/proc/cpuinfo", 800)
    if cpu_raw:
        parts.append(hashlib.sha256(cpu_raw.encode()).hexdigest()[:16])
    else:
        parts.append("")

    # 3. 内存总量（MB）
    mem_total = ""
    try:
        with open("/proc/meminfo") as f:
            first_line = f.readline()
            # MemTotal:       4096000 kB
            kb = int(''.join(filter(str.isdigit, first_line.split("kB")[0])))
            mem_total = str(kb // 1024)  # 转 MB
    except Exception:
        pass
    parts.append(mem_total)

    # 4. 进程/容器维度（让同设备不同容器有区别）
    parts.append(str(os.getpid()))           # 当前进程ID
    parts.append(str(os.getppid()))           # 父进程ID

    # 5. 主机名
    hostname = _run(["hostname"]) or _safe_read("/etc/hostname") or ""
    parts.append(hostname)

    # 6. 系统固定盐
    parts.append(SYSTEM_SALT)

    return "|".join(parts)


def generate_machine_code():
    """生成机器码（首次）或读取本地缓存（已存在）"""
    # 优先读本地缓存
    if os.path.exists(MACHINE_CODE_FILE):
        try:
            code = open(MACHINE_CODE_FILE, "r", encoding="utf-8").read().strip()
            if len(code) == 64:  # SHA256格式校验
                return code, False  # False = 读缓存
        except Exception:
            pass

    # 首次生成
    raw = collect_device_fingerprint()
    code = hashlib.sha256(raw.encode()).hexdigest()

    # 写本地文件（权限600，仅本人可读写，防误删）
    with open(MACHINE_CODE_FILE, "w", encoding="utf-8") as f:
        f.write(code)
    os.chmod(MACHINE_CODE_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600

    return code, True  # True = 新生成


def main():
    machine_code, is_new = generate_machine_code()

    print()
    print("=" * 60)
    print("  松哥系统 - 机器码")
    print("=" * 60)
    print()

    if is_new:
        print("  [首次生成] 机器码已生成，已永久保存到本地")
    else:
        print("  [已激活] 读取本地保存的机器码")

    print()
    print(f"  {machine_code}")
    print()

    print("  " + "-" * 56)
    print("  使用说明：")
    print("  1. 将上方机器码截图发给松哥")
    print("  2. 松哥激活后即可使用松哥系统")
    print("  3. 机器码永久有效，换手机需重新获取")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()