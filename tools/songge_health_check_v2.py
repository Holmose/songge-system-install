#!/usr/bin/env python3
"""松哥系统健康检查 V2：发布前质量门。只读检查。"""
from pathlib import Path
import json, re, subprocess, sys

ROOT=Path('/var/minis')
SK=ROOT/'skills'
MEM=ROOT/'memory/songge'
REQ_SKILLS=['songge-dispatch','songge-state-router','songge-action-router','songge-wenzhong','songge-youqu','songge-shenmi','songge-shengwen','songge-huishou','songge-mbti','songge-anti-burnout','songge-attract-display','songge-moments','songge-close-deal','songge-case-review','songge-workflow','songge-publish']
REQ_KNOW=['03-cooperation-level.md','04-state-router.md','11-window-system.md','17-taboo-list.md','27-attraction-display-philosophy.md','28-display-chat-bridge.md']
BAD_TERMS=['simp-skill','防耗尽','焦虑驱动','MBTI性格校正','MBTI分析校正','客户档案系统','客户档案']
DIRECT_INVITES=['周六有空吗','那就见面聊聊','想见就见','我们见一面吧']

class R:
    def __init__(self): self.ok=[]; self.warn=[]; self.fail=[]
    def add(self, lvl, msg): getattr(self,lvl).append(msg)
    def show(self):
        print('# 松哥系统健康检查 V2')
        for name, arr in [('FAIL',self.fail),('WARN',self.warn),('OK',self.ok)]:
            print(f'\n## {name} ({len(arr)})')
            print('\n'.join('- '+x for x in arr) if arr else '- 无')
        return 1 if self.fail else 0

def read(p):
    try: return p.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''

def check_skills(r):
    miss=[]
    for s in REQ_SKILLS:
        p=SK/s/'SKILL.md'
        if not p.exists(): miss.append(s)
    r.add('fail' if miss else 'ok', '核心Skill缺失：'+','.join(miss) if miss else f'核心Skill存在：{len(REQ_SKILLS)}个')

def check_knowledge(r):
    miss=[]
    for k in REQ_KNOW:
        if not (MEM/'knowledge'/k).exists(): miss.append(k)
    r.add('fail' if miss else 'ok', '核心知识文件缺失：'+','.join(miss) if miss else f'核心知识文件存在：{len(REQ_KNOW)}个')

def check_naming(r):
    hits=[]
    for base in [SK/'songge-dispatch',SK/'songge-state-router',SK/'songge-action-router',SK/'songge-mbti',SK/'songge-anti-burnout',MEM/'clients']:
        if not base.exists(): continue
        for p in base.rglob('*'):
            if p.is_file() and p.suffix in ('.md','.py','.json') and '.git' not in str(p):
                s=read(p)
                for t in BAD_TERMS:
                    if t in s: hits.append(f'{p}:{t}')
    r.add('fail' if hits else 'ok', '旧命名/外源残留：'+'; '.join(hits[:8]) if hits else '命名体系通过：无旧词残留')

def check_invite(r):
    roots=[SK/'songge-shengwen',SK/'songge-wenzhong',SK/'songge-action-router']
    needed=['邀约前置','感觉铺垫','场景植入']
    corpus='\n'.join(read(p) for root in roots for p in root.rglob('*.md'))
    miss=[x for x in needed if x not in corpus]
    risky=[]
    for root in roots:
        for p in root.rglob('*.md'):
            s=read(p)
            for q in DIRECT_INVITES:
                if q in s and '禁用反例' not in s[max(0,s.find(q)-80):s.find(q)+80]: risky.append(f'{p}:{q}')
    if miss or risky: r.add('fail','邀约前置检查失败：缺失='+','.join(miss)+' 风险='+';'.join(risky[:5]))
    else: r.add('ok','邀约前置机制通过：有铺垫/场景/自然邀约，风险话术已标注')

def check_clients(r):
    d=MEM/'clients'
    tools=['clients_db.py','clients_sync.py','clients_to_holo.py','README.md']
    miss=[t for t in tools if not (d/t).exists()]
    r.add('fail' if miss else 'ok','关系档案层缺失：'+','.join(miss) if miss else '关系档案层工具齐全')
    if (d/'clients_db.py').exists():
        try:
            out=subprocess.run(['python3',str(d/'clients_db.py'),'list'],capture_output=True,text=True,timeout=15)
            r.add('ok' if out.returncode==0 else 'warn','clients_db.py list 可运行' if out.returncode==0 else 'clients_db.py list 异常')
        except Exception as e: r.add('warn','clients_db.py 执行异常：'+str(e))

def check_tests(r):
    missing=[]
    for s in ['songge-dispatch','songge-state-router','songge-action-router','songge-wenzhong','songge-youqu','songge-shenmi','songge-shengwen','songge-huishou']:
        if not (SK/s/'test-prompts.json').exists(): missing.append(s)
    r.add('warn' if missing else 'ok','缺少test-prompts：'+','.join(missing) if missing else '核心测试Prompt齐全')
    runner=SK/'songge/tools/songge_test_runner.py'
    if runner.exists():
        try:
            out=subprocess.run(['python3',str(runner),'all'],capture_output=True,text=True,timeout=30)
            r.add('ok' if out.returncode==0 else 'fail','自动测试Runner通过' if out.returncode==0 else '自动测试Runner失败')
        except Exception as e:
            r.add('fail','自动测试Runner异常：'+str(e))
    else:
        r.add('fail','缺少自动测试Runner')

def check_p6_module_redirect(r):
    targets=[SK/'songge/tools/songge_feedback_loop.py', MEM/'clients/clients_sync.py', MEM/'clients/clients_to_holo.py', MEM/'clients/clients_index.py', SK/'songge/tools/songge_status.py']
    miss=[]
    for p in targets:
        s=read(p)
        if '--mode' not in s and "mode='master'" not in s:
            miss.append(str(p))
    r.add('fail' if miss else 'ok','P6-2 模块接管缺失：'+','.join(miss[:5]) if miss else 'P6-2 模块接管通过')
def check_publish_files(r):
    d=SK/'songge-publish'
    miss=[x for x in ['songge_publish_v3.py','songge_publish_gitee_fixed.py','install_module.py'] if not (d/x).exists()]
    r.add('fail' if miss else 'ok','发布文件缺失：'+','.join(miss) if miss else '发布脚本齐全')
    tool_miss=[x for x in ['songge_dashboard.py','songge_status.py','songge_changelog.py','songge_feedback_loop.py','songge_package_verify.py','songge_test_runner.py'] if not (SK/'songge/tools'/x).exists()]
    r.add('fail' if tool_miss else 'ok','企业化工具缺失：'+','.join(tool_miss) if tool_miss else '企业化工具齐全')
    mem_miss=[]
    for p in ['users_registry.json','users_manager.py','path_resolver.py']:
        if not (MEM/p).exists():
            mem_miss.append(p)
    r.add('fail' if mem_miss else 'ok','P6路径隔离底座缺失：'+','.join(mem_miss) if mem_miss else 'P6路径隔离底座齐全')


def main():
    r=R()
    for f in [check_skills,check_knowledge,check_naming,check_invite,check_clients,check_tests,check_p6_module_redirect,check_publish_files]: f(r)
    code=r.show()
    if code: print('\n❌ 发布前质量门：不通过')
    else: print('\n✅ 发布前质量门：通过')
    sys.exit(code)
if __name__=='__main__': main()
