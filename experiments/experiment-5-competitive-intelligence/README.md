# 实验五：竞争情报分析引擎（v0.5）

本实验把实验3的蓝牙降噪耳机产品记录转换成可复算的竞争情报指标，回答四个问题：主要竞争者是谁、竞争发生在哪些维度、威胁来自哪里、样本中有哪些市场空白。

数据是课堂模拟数据。互动量、评分和价格只用于演示分析流程，不能当作真实市场份额或商业决策依据。

## 指标与口径

竞争威胁指数固定为：

```text
威胁指数 = 消费者重合度 × 30%
         + 产品重合度 × 25%
         + 价格重合度 × 20%
         + 品牌热度 × 25%
```

权重合计 100%，每个分项均归一化到 0–100：

- 消费者重合度：竞争品牌互动量相对焦点品牌的比例；互动量为 `review_count + likes + favorites`，最高按 100 分计。
- 产品重合度：每个竞争产品与焦点品牌产品的最近邻相似度，使用价格、使用体验、降噪和续航的可用字段。
- 价格重合度：竞争产品与焦点品牌最近价格的指数衰减相似度。
- 品牌热度：品牌总互动量相对样本最高品牌的比例。

焦点品牌默认是 `NovaPulse(新脉)`。如果输入中不存在该品牌，程序会自动选择互动量最高的品牌，并在 `summary.json` 与结论报告中说明原因。

实验4的 `positive / mixed / negative` 标签词汇被复用为产品评分标签：`≥4.3` 为 positive，`3.7–4.29` 为 mixed，`<3.7` 为 negative。实验4的咖啡评论文本不会被冒充为耳机评论；标签来源和阈值记录在输出中。

## 运行

从仓库根目录执行：

```powershell
python experiments/experiment-5-competitive-intelligence/src/competitive_intelligence.py
```

也可以显式指定输入和输出目录：

```powershell
python experiments/experiment-5-competitive-intelligence/src/competitive_intelligence.py `
  --input experiments/experiment-3-bluetooth-anc/data/processed/clean_data.csv `
  --output-dir experiments/experiment-5-competitive-intelligence/outputs
```

## 提交物

- `src/competitive_intelligence.py`：校验、缺失处理、指标计算、敏感性分析和交付物生成。
- `outputs/indicator_dictionary.csv`：指标、单位、权重、公式、来源和缺失处理。
- `outputs/brand_comparison.csv`：品牌价格、评分、产品数量、互动量和性能对比。
- `outputs/threat_ranking.csv`：四个维度和加权威胁指数。
- `outputs/price_bands.csv`、`outputs/product_structure.csv`：价格带和产品结构。
- `outputs/evaluation_selling_points.csv`：品牌评价标签与结构化卖点维度。
- `outputs/market_gaps.csv`：价格带 × 降噪 × 续航的低覆盖候选空白。
- `outputs/label_summary.csv`：复用实验4词汇后的评分标签分布。
- `outputs/evidence_index.csv`：每条证据带 `evidence_id`、`record_id`、源文件和源字段，可回到实验3清洗数据。
- `outputs/sensitivity_check.csv`：等权、单维度加权等场景下的排名变化。
- `outputs/data_quality.csv`：缺失值、插补和被排除行的记录。
- `outputs/dashboard.html`：无需依赖安装、可直接打开的竞品 Dashboard。
- `outputs/conclusion_report.md`：事实、推断、机会和限制分层的结论报告。
- `outputs/summary.json`：版本、焦点品牌、权重校验和首位竞争者。

## 验收检查

```powershell
python -m unittest discover -s experiments/experiment-5-competitive-intelligence/tests -v
```

验收包括：权重合计 100%、输入记录唯一且数量稳定、威胁指数可复算、证据索引可回溯、敏感性场景权重合计 100%。
