# 老师面前如何跑通流程（2026-11-17）

这是当前电脑上可以照着做的演示路线。先用 AI 读取原版 Skill 产出测试方案，再用网页演示数据计算、下载报告，最后让 AI 按 Skill 复盘。Skill 由对话中的 AI 使用；网页按钮目前只运行 Python 规则，没有连接大模型。

## 演示前先分清当前状态

| 内容 | 当前状态 | 能演示什么 |
|---|---|---|
| GitHub 原版 ab-testing Skill | 已下载原文、参考文件和 MIT 许可证，固定提交并逐字节验证 | 来源、版本和实际读取过程 |
| 瑞幸/库迪广告对比 | 已有匹配模板方案，尚无真实素材和受试者数据 | 测试设计，不是哪个品牌胜出 |
| 网页默认数据 | Campus Coffee 的 120 条模拟评论、60 条模拟 A/B 记录 | 输入、计算、证据、报告、运行历史 |
| 完整真实用户测试 | 尚未执行 | 需要真实素材、招募、预先确定指标和匿名数据 |

不能把 Campus Coffee 的默认 A/B 数据改称“瑞幸组/库迪组”。现有网页也没有实现七分量表的购买意愿分析、随机分配问卷或置信区间；`purchased` 表示二元购买记录，不能拿购买意愿代替。旧方案中这些功能是待实现的设计，不是现有功能。

## 第一步：现场展示 Skill 来源（约1分钟）

项目目录：`C:\codex_homework\experiments\experiment-8-ai-marketing-os`。

打开以下文件给老师看：

- `vendor/marketingskills/ab-testing/SKILL.md`：GitHub 原版，版本 2.0.7。
- `vendor/marketingskills/LICENSE`：原 MIT 许可证。
- `vendor/marketingskills/PROVENANCE.json`：来源、固定提交和 SHA-256。

源仓库：<https://github.com/coreyhaines31/marketingskills/tree/7c187944fa63d149879459ba53ef4fd3c0364c50/skills/ab-testing>。

可以讲：“这是我引用的现成 Skill，规定先提出假设、一次测试一个变量、定义主指标、提前确定样本和停止规则。它是 AI 的操作说明，不是 Python 可执行文件。”

## 第二步：在对话里让 AI 真正用 Skill（约2分钟）

以下内容复制到 AI 对话框，不是 PowerShell：

```text
项目是 C:\codex_homework\experiments\experiment-8-ai-marketing-os。
请先完整读取 vendor/marketingskills/ab-testing/SKILL.md，
以及它的 references/test-templates.md 和 references/sample-size-guide.md。
按原版 Skill 为瑞幸和库迪设计课堂问卷测试，主指标是购买意愿。
目前没有真实广告文件和用户数据，请将素材和结论标为待验证。
先说明比较完整广告与比较品牌标识分别能回答什么问题；
本次选择相同模板、只改变品牌标识，各组计划30名成年参与者，
只作探索性课堂研究，不能预设赢家或声称具有充分统计功效。
生成假设、A/B版本说明、问卷题目、随机分组方案、指标、
停止规则与局限，保存到 docs/live_ab_plan.md。
记录具体用了 Skill 的哪些章节，保存到 docs/live_skill_usage.md。
不要用现有 Campus Coffee 模拟结果替代瑞幸/库迪的真实数据。
```

确认对话中真的读取了原版文件，再打开生成的两个文件。没有提交这段指令前，`live_ab_plan.md` 与 `live_skill_usage.md` 不会自动出现；网页按钮也不会生成它们。

## 第三步：启动网页（约1分钟）

当前电脑已有 Python 和 Streamlit，无需先安装。双击项目内 `start_demo.cmd`，也可以打开 PowerShell 并输入：

```powershell
cd "C:\codex_homework\experiments\experiment-8-ai-marketing-os"
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

浏览器打开 <http://127.0.0.1:8503>。运行期间保留终端窗口，停止时按 Ctrl+C。

点击左侧“运行整套 Marketing OS”，等待绿色“运行完成”提示和新的 `OS-...` 编号。网页可能先显示已有报告，因此只打开网页不能证明执行了新计算，应点击按钮后展示新运行编号。

默认不用上传。如果老师要看上传，四个框分别选择：

| 上传框 | 项目内文件 |
|---|---|
| 品牌档案 JSON | `data/brand_profile.json` |
| 消费者数据 CSV | `data/consumer_reviews.csv` |
| 竞品数据 CSV | `data/competitors.csv` |
| 匿名 A/B/问卷 CSV | `data/ab_test_anonymous.csv` |

当前界面要求上传时四个都提供，不能只换一个 CSV。使用同一套演示数据，不要混搭不同品类的数据。

## 第四步：展示结果和证据（约2分钟）

依次点“品牌档案 → 消费者洞察 → 竞品情报 → 内容机会 → Campaign Planner → 效果分析 → 证据与下载 → 历史记录”。

- 消费者洞察：展示 120 条模拟评论、主题计数，选一个 `CC-R...` ID，在原始评论 CSV 搜索对应行。
- 内容机会：当前竞品覆盖系数为程序内置示例值，不能称为自动采集的真实广告覆盖率。
- 效果分析：A、B 各30条模拟记录；A 点击20、购买4，B 点击22、购买0。只说明计算流程，不评价真实品牌。
- 证据与下载：下载 `analysis_report.md`、`ab_group_results.csv` 或完整 JSON。
- 历史记录：显示本次运行编号和时间，证明重新运行并保存过。

纯命令行演示也可以执行 `python run.py`；出现 `"status": "completed"` 并在 `outputs/` 看到新报告即代表核心计算完成。

## 第五步：按 Skill 复盘并提出下一轮（约1分钟）

在 AI 对话里发送：

```text
请读取实验八 vendor/marketingskills/ab-testing/SKILL.md 的
Analyzing Results 和 Documentation 章节，
然后检查 data/ab_test_anonymous.csv、data/generate_sample_data.py
和 outputs/marketing_os_run.json。
用程序独立核对样本、点击、购买和提升幅度。
这是模拟数据，请区分“程序算出来的数”和“真实营销结论”。
按主指标、次指标、缺失证据和样本限制复盘，不宣布品牌赢家，
提出下一轮待验证假设，保存到 reports/live_skill_review.md。
```

可先查看 `reports/ab_testing_skill_review_2026-11-17.md`，它记录了本次实际按原版 Skill 复核的结果。

## GitHub 留痕和测试说明

本次原版 Skill、课堂操作说明和复核报告会作为一次独立提交留在实验八目录。现场新生成的文件也应检查后单独提交。

需要演示自动化检查时，在第二个 PowerShell 窗口运行：

```powershell
cd "C:\codex_homework\experiments\experiment-8-ai-marketing-os"
python -m unittest discover -s tests -v
```

2026-11-17 实测：5项现有测试通过；另在隔离临时目录用 Streamlit AppTest 点击运行按钮，8个标签页渲染无异常、5个输出文件生成、数据库保存成功。陌生数据测试仅有一个小样本功能用例，不能称为大规模压力测试已完成。

若8503端口已占用，可将启动命令中的端口改成8504，再打开对应地址。若缺少 Streamlit，用 `python -m pip install -r requirements.txt` 安装后重试。当前验证环境为 Python 3.14.3 / Streamlit 1.56.0 / pandas 3.0.2；现有 requirements 的 pandas 范围排除3.x，不代表已在其声明的全部版本范围验证。

最后可讲：“我先让 AI 按公开 Skill 设计实验，再用程序完成模拟数据的计算和追溯，最后按同一 Skill 复盘。真实瑞幸/库迪素材和用户测试仍待完成。”
