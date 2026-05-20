# 设备绑定操作手册（主控机免检 + 学员端强检）

## 1) 一次性准备（主控机）

1. 设置签名密钥（只在你主控机设置，不下发学员）
   - 变量名：`SONGGE_LICENSE_SECRET`
2. 获取主控机设备哈希：
   - `python3 /var/minis/skills/songge/tools/songge_license_guard.py device`
3. 写入策略白名单：
   - 编辑 `/var/minis/skills/songge/data/license_policy.json` 的 `master_devices`

## 2) 学员端绑定

1. 学员先发设备哈希：
   - `python3 /var/minis/skills/songge/tools/songge_license_guard.py device`
2. 在学员设备上发证：
   - `python3 /var/minis/skills/songge/tools/songge_license_guard.py issue --student-id 学员名 --days 30`
3. 学员校验：
   - `python3 /var/minis/skills/songge/tools/songge_license_guard.py check`

## 3) 门控接入点（强制）

在以下入口执行 check：
- songge-dispatch
- songge-analysis-mode
- songge-workflow（输出前）

若返回非 `PASS_MASTER` 或 `PASS_LICENSE`，统一拒绝：

`未检测到有效设备授权，系统拒绝分析与输出。请先完成绑定。`

## 4) 注意

- 换机需重绑。
- 学员复制 `license.json` 到其他设备会因 `device_hash` 不一致而失败。
- 不要把 `SONGGE_LICENSE_SECRET` 发给学员。
