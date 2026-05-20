# 学员端授权标准流程（V3 非对称）

## 学员步骤

### Step 1：更新到新版本
执行你发的安装更新命令。

### Step 2：回传机器码
学员执行：

```bash
python3 /var/minis/skills/songge/tools/songge_license_guard.py device
```

把输出里的 `device_hash` 发给你。

### Step 3：接收授权包并安装
收到你发的授权包后，执行你给的安装命令。

### Step 4：自检授权

```bash
python3 /var/minis/skills/songge/tools/songge_license_guard.py check
```

返回 `PASS_LICENSE` 即为成功。

---

## 主控机（你）步骤

### 1）签发授权

```bash
python3 /var/minis/skills/songge/tools/manage_license.py issue --student-id <学员ID> --device-hash <学员device_hash> --days 30
```

### 2）查看授权台账

```bash
python3 /var/minis/skills/songge/tools/manage_license.py list
```

### 3）续期

```bash
python3 /var/minis/skills/songge/tools/manage_license.py renew --student-id <学员ID> --days 30
```

### 4）吊销

```bash
python3 /var/minis/skills/songge/tools/manage_license.py revoke --student-id <学员ID>
```

---

## 说明

- 更新系统不等于自动授权。
- 每台设备必须单独绑定 `device_hash`。
- 授权失败一律拒绝分析与输出。
