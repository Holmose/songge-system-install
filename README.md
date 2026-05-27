# 松哥撩妹系统

学员端安装系统，设备绑定授权。

## 安装方式

```bash
curl -sSL https://gitee.com/holmose/songge-system-install/raw/master/setup.sh | bash
```

或 GitHub（备用）：

```bash
curl -sSL https://github.com/Holmose/songge-system-install/raw/main/setup.sh | bash
```

安装后输入密码完成安装。

## 版本信息

- 当前版本：v20260528
- 设备码盐值：SONGGE_LICENSE_V1_2025

## 文件说明

| 文件 | 说明 |
|------|------|
| `setup.sh` | 一键安装脚本 |
| `_pkg.bin` | 加密系统包 |
| `tools/` | 系统工具（含设备码生成） |
| `MinisApp-*.apk` | Minis App 安装包 |
| `darwin-skill.zip` | 达尔文优化技能包 |

## 学员激活流程

1. 安装系统后运行 `python3 get_device_hash.py` 获取设备码
2. 将设备码发给松哥
3. 松哥激活后即可使用松哥系统

## 技术支持

联系松哥获取激活支持。
