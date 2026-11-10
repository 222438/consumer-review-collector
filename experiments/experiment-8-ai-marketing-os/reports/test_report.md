# 实验八测试报告

运行命令：

```text
python run.py
python -m unittest discover -s tests -v
python -m py_compile src/marketing_os.py app.py run.py
```

验收覆盖：

| 项目 | 结果 |
|---|---|
| 品牌档案字段与版本 | 通过 |
| 消费者评分、主题多标签和 evidence_refs | 通过 |
| 竞品排名、威胁维度和机会缺口 | 通过 |
| Campaign 目标、渠道、KPI、风险与人工门 | 通过 |
| A/B 两组各≥20人、点击/购买/反馈指标 | 通过 |
| SQLite 历史运行记录 | 通过 |
| Streamlit 模块语法检查 | 通过 |

示例结果来自匿名课堂模拟数据；这份测试报告证明代码链路和数据校验可运行，不把模拟结果宣称为真实用户研究结果。正式提交前应将经授权的真实匿名数据替换到同样的字段契约，并重新运行报告。
