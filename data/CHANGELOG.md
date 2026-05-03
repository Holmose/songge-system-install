# songge data change log

## 2026-05-04 客户库结构补全

变更文件：
- `/var/minis/skills/songge/data/clients.json`
- `/var/minis/skills/songge/data/songge_query.py`

备份：
- `/var/minis/skills/songge/data/backups/clients_20260504_before_structure_fill.json`

变更内容：
1. 所有客户补齐 `当前状态`、`微信备注`、`raw_chat_files`、`case_ids` 字段。
2. 已有旧状态字段归一到新版状态结构：阶段/证据/配合度/窗口三要素/风险/推荐动作/禁止动作/推荐技能/依据。
3. 无聊天证据的客户标“信息不足”，不凭空判断。
4. 关联已有案例：颜、芙芙。
5. 关联 raw 聊天文件：思敏、敏敏。
6. 查询脚本修正 strengths/weaknesses 显示，并新增当前状态/关联输出。

保护说明：
- 未删除、未覆盖、未清洗任何 raw 聊天文件。
- `chats_raw/`、`clients_profile/`、`case-logs/` 文件哈希复核未变。
