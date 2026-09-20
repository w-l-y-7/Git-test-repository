---
name: git-save
description: 一键提交并推送：先扫一遍垃圾文件（依赖缓存、IDE/系统文件、密钥、脚本产物）写进 .gitignore，再并行检查（单元测试 + 质量审查），都通过后才 git add + git commit + git push 到 GitHub。用户输入 /git-save、或说"提交"、"保存代码"、"存档"、"推送"、"保存到 GitHub" 的时候使用。检查没通过会拦下，不提交。
---

# git-save：先检查，再保存并推送代码

## 这个技能做什么

把当前所有改动自动完成五步：

0. **先扫垃圾文件**：把不该入库的（依赖缓存、IDE/系统文件、密钥、脚本产物）认出来写进 .gitignore
1. **拿改动清单**
2. **并行跑两道检查**：质量审查（quality-engineer）+ 单元测试（tester）
3. **都通过** → git add + git commit
4. **git push** 推送到 GitHub

检查没通过就拦下来、不提交。这是项目现在唯一的提交方式，也受 pre-commit hook 双重保护。

## 执行步骤

### 第零步：先扫垃圾文件（提交前必做）

跑检查 agent 之前先过一遍，别让不该入库的文件混进来。这一步合并了原 git-ignore 技能。

**0.1 收集情报**（路径统一加 `-c core.quotepath=false`，中文文件名才不乱码）：

```powershell
# 没被跟踪、现在也没被忽略的文件（= 下次提交会带上的）
git -c core.quotepath=false ls-files --others --exclude-standard

# 已被跟踪的文件全名单（= 拿来认漏网的垃圾）
git -c core.quotepath=false ls-files
```

再读一遍现有 `.gitignore`（UTF-8），记住已有哪些规则，别重复加。

**0.2 归类**，对照下表认人：

| 类别 | 特征 | 例子 |
| --- | --- | --- |
| **B 依赖/缓存目录** | `node_modules`、`.venv`、`venv`、`__pycache__`、`.pytest_cache`、`.mypy_cache`、`dist`、`build`、`.next`、`*.pyc` | 删了能重装 |
| **C IDE/系统文件** | `.vscode`、`.idea`、`.DS_Store`、`Thumbs.db`、`desktop.ini`、`*.swp` | 每台电脑都不一样 |
| **D 隐私/密钥** | `.env*`、`*.pem`、`*.key`、`*.p12`、`*.db`、`*.sqlite*` | 提交等于泄露 |
| **A 脚本产物** | `*.csv`、`*.png`、`*.log`、`*.aux`、`*_report.csv` 这类，且名字像「跑一次脚本生成的」 | 重跑就能再生成 |

三条铁律：**源代码、脚本、文档、配置文件一律不算垃圾**；一条规则只写具体路径，别写一刀切的 `*.csv`、`*.png`；拿不准就放进待问清单，别擅自归类。

**0.3 B / C / D 直接拦下不问**，写进 `.gitignore`。D 类拦下后要在汇报里点名提醒用户。

**0.4 A 类和拿不准的列一次清单问用户**（AskUserQuestion 或直接对话），每项标上类别，并明确告诉用户哪些是建议提交的代码。用户说都不要就跳过。

**0.5 写进 .gitignore**，放带标记的分区：

```
# ===== git-ignore 自动整理 <今天的日期> =====
## B 依赖/缓存目录
...
```

文件已存在就只**追加**，绝不整体重写（旧文件里可能有被 GBK 写坏的乱码注释，一重写就真坏）；不存在就用 Write 新建 UTF-8 无 BOM。加之前跟现有规则去重；子目录已有 `.gitignore` 且覆盖了，就别在根目录重复加。

**0.6 已跟踪的垃圾**靠取消跟踪清掉，**必须问过用户再动**：

```powershell
git rm --cached "相对路径/文件名"
```

`--cached` 只从 git 账本里划掉，硬盘上的文件原样保留。绝不能漏掉 `--cached`，漏了就是真删用户文件。

### 第一步：拿改动清单

用两条命令拿所有改动（已改的跟踪文件 + 未跟踪的新文件），去并集：

```powershell
git -c core.quotepath=false diff --name-only
git -c core.quotepath=false ls-files --others --exclude-standard
```

- 合并结果，路径统一成**正斜杠相对路径**（`\` 换成 `/`）。
- 清单是空的 → 告诉用户「没有改动，不用提交」，结束。
- `save-gate/` 下的标记文件被 gitignore 了，不会出现在清单里。

### 第二步：并行跑两个检查 agent

用 Agent 工具，在**同一条消息**里同时调用两个 subagent，把清单传给它们：

- `subagent_type: quality-engineer`，审查清单里所有文件
- `subagent_type: tester`，测试清单里所有文件

它们并行执行。**传清单时明确告诉每个 agent：清单里有这些文件，全部检查，别再问用户。**

### 第三步：确认两道检查都通过

等两个 agent 都完成后，读 `save-gate/test.passed` 和 `save-gate/quality.passed`：

- 两个文件都在、且第 1 行都是 `PASS` → 通过，进入第四步。
- 任一文件缺失或不是 `PASS` → **不提交**，把没通过的那个 agent 的结论告诉用户，说明「改完再重新提交」。

### 第四步：提交并推送

1. 问提交信息（或触发时就带了）——一句话说清"这次做了什么"。
2. `git add -A`
3. `git commit -m "提交信息"`
4. 推送（关键：先设环境变量，否则登录窗口弹不出来）：

```powershell
$env:GCM_INTERACTIVE='always'
git push
```

推送时屏幕会弹 GitHub 登录窗口，提醒用户登录。

### 第五步：推送成功后，清掉旧通行证

提交和推送都成功后，**立刻删除两张旧通行证**（`save-gate/test.passed` 和 `save-gate/quality.passed`）。不然下一轮提交会拿旧标记冒充，跟新改动对不上：

```powershell
Remove-Item -Force save-gate/test.passed, save-gate/quality.passed
```

删不掉或文件不在没关系，下一轮检查会自动重新生成。

## 注意事项

- **绝不忽略源代码、脚本、文档、配置文件**——那是用户的成果，第零步的作用是拦垃圾，不是拦劳动成果。
- **绝不 `git rm`（不带 `--cached`）真删文件**；最多 `git rm --cached`。
- **如果 `git commit` 被 pre-commit hook 拦截**（报 save-gate/test.passed 或 quality.passed 相关错误），说明标记没对上或过期。**不要用 `--no-verify` 绕过**，把原因告诉用户，重新提交跑一次完整流程。
- **绝对不要用 `git push --force`**，会覆盖远程已有的提交，很危险。
- 如果 `git push` 报错（比如远程有冲突），别自己乱处理，把报错信息告诉用户。
- 推送成功后跟用户说一句「已存好档并推送」，确认完成。
