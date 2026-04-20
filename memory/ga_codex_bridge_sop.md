# GA↔Codex 桥接 SOP
<!-- aliases: ga-codex|ga-ask|codex-bridge|桥接 -->

## 架构概览
```
GA (Windows)                          Codex (WSL)
┌─────────────┐  ga-codex.bat/py  ┌──────────────┐
│ ga-codex.py │ ──wsl──bash──c──→ │ codex exec   │
│ --json      │ ←──JSONL──────── │ --json        │
│ --async     │   stdout          │               │
└─────────────┘                    └──────────────┘

Codex (WSL)                          GA (Windows)
┌─────────────┐  ga-ask.bat/py   ┌──────────────┐
│ codex skill │ ──cmd.exe──────→ │ ga-ask.py    │
│ ga-bridge   │ ←──stdout─────── │ (HTTP API)   │
└─────────────┘                    └──────────────┘
```

## 关键文件
| 文件 | 位置 | 职责 |
|------|------|------|
| ga-codex.py | D:\code\GenericAgent\ | GA→Codex: WSL调用codex exec, JSONL解析 |
| ga-codex.bat | D:\code\GenericAgent\ | bat封装: chcp 65001 + -X utf8 + python调用 |
| ga-ask.py | D:\code\GenericAgent\ | Codex→GA: HTTP接口, timeout/progress |
| ga-ask.bat | D:\code\GenericAgent\ | bat封装, 被codex ga-bridge skill调用 |
| SKILL.md | ~/.codex/skills/ga-bridge/ | codex端skill, 触发ga-ask.bat |
| sessions.json | codex-bridge/ | session持久化(thread_id↔codex session) |
| roles/*.md | codex-bridge/roles/ | 角色prompt (reviewer/debugger/architect/analyzer) |

## 关键前置
1. Codex API额度正常 (usage limit时返回exit_code=1)
2. WSL Ubuntu_01_25 可用, codex已登录
3. bat必须用 `.venv\Scripts\python.exe` 绝对路径, 禁裸python
4. bat首行 `chcp 65001` 防GBK乱码

## 典型坑
1. **Heredoc注入**: prompt含heredoc delimiter (GA_CODEX_EOF) 会提前终止→已加sanitize替换
2. **Workdir引号注入**: workdir含`"`会break bash引号→已加strip
3. **JSONL解析**: codex exec --json输出多行JSONL, 需逐行parse, 跳过非JSON行
4. **Session role=null**: 旧sessions.json无role字段是历史遗留, 新创建的已正确存role
5. **Timer kill后stdout阻塞**: proc.kill()后for-line-in-stdout可能卡住 (已知边界, 待重构)
6. **--progress默认True**: 用`store_true`+`default=True`+`--no-progress`, 逻辑靠`not args.no_progress`

## 调用示例
```bash
# GA→Codex (JSON模式)
ga-codex.bat --json --timeout 300 "explain this code"

# GA→Codex (带进度显示)
ga-codex.bat --progress --timeout 600 "review ga-codex.py"

# GA→Codex (续接session)
ga-codex.bat --session THREAD_ID "follow up question"

# Codex→GA (从codex内)
cmd.exe /c "D:\code\GenericAgent\ga-ask.bat" --json --timeout 300 "read file X"
```

## 测试状态
- ✅ GA→Codex: --json输出/编码/session/错误处理 已验证
- ⏸️ 完整端到端测试: 待Codex API额度恢复(2026-04-28)