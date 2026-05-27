#!/usr/bin/env python3
"""松哥系统发布包完整性校验。"""
from pathlib import Path
import tarfile, tempfile, sys, os, json
PKG=Path('/var/minis/workspace/songge_system_backup.tar.gz')
REQ=[
 'skills/songge-dispatch/SKILL.md','skills/songge-state-router/SKILL.md','skills/songge-action-router/SKILL.md',
 'skills/songge-wenzhong/SKILL.md','skills/songge-youqu/SKILL.md','skills/songge-shenmi/SKILL.md','skills/songge-shengwen/SKILL.md','skills/songge-huishou/SKILL.md',
 'skills/songge-mbti/SKILL.md','skills/songge-anti-burnout/SKILL.md',
 'skills/songge/tools/songge_license_guard.py','skills/songge/tools/songge_package_verify.py',
 'memory/songge/knowledge/11-window-system.md','memory/songge/clients/clients_db.py','memory/songge/clients/clients_index.py','memory/songge/songge_system_dependency_map.md'
]
FORBID=['.git/','__pycache__/','memory/songge/case-logs/','memory/songge/customer-profile/','memory/songge/content/']

def main(pkg=PKG):
    if not pkg.exists():
        print(f'❌ 包不存在：{pkg}'); return 1
    fails=[]; oks=[]
    with tarfile.open(pkg,'r:gz') as t:
        names=[n.lstrip('./') for n in t.getnames()]
    ns=set(names)
    for r in REQ:
        if r in ns: oks.append(r)
        else: fails.append('缺失必需文件：'+r)
    for n in names:
        for f in FORBID:
            if f in n: fails.append('发现禁止路径：'+n); break
    # 禁止具体关系对象目录被打包：clients/{name}/profile.md
    for n in names:
        if n.startswith('memory/songge/clients/') and n.count('/')>=3:
            rest=n[len('memory/songge/clients/'):]
            if '/' in rest and not rest.startswith('__'):
                fails.append('发现具体关系档案目录：'+n); break
    print('# 发布包完整性校验')
    print(f'包：{pkg}')
    print(f'文件数：{len(names)}')
    print(f'OK：{len(oks)}')
    if fails:
        print('## FAIL')
        for x in fails[:20]: print('- '+x)
        print('\n❌ 发布包校验不通过')
        return 1
    print('✅ 发布包校验通过')
    return 0
if __name__=='__main__':
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv)>1 else PKG))
