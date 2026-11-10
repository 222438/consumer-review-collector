"""Streamlit UI for Experiment 8.

Run from this directory with ``streamlit run app.py``.  The same workflows can
be executed without Streamlit through ``python run.py`` or the module API.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
from marketing_os import (  # noqa: E402
    DataValidationError,
    analyze_competitors,
    analyze_consumer_data,
    analyze_experiment_effect,
    calculate_content_opportunities,
    history,
    load_brand_profile,
    load_reviews,
    plan_campaign,
    run_os,
)

DATA = HERE / "data"
OUTPUT = HERE / "outputs"
DB = HERE / "data" / "marketing_os.sqlite3"


def _table(rows: list[dict]) -> None:
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("暂无数据")


def main() -> None:
    st.set_page_config(page_title="AI Marketing OS", page_icon="📈", layout="wide")
    st.title("AI Marketing OS")
    st.caption("实验八 · 数据 → 洞察 → 决策 → 内容 → 测试 → 优化（v1.0）")
    with st.sidebar:
        st.header("运行配置")
        brand_file = st.file_uploader("上传品牌档案 JSON", type=["json"])
        review_file = st.file_uploader("上传消费者数据 CSV", type=["csv"])
        competitor_file = st.file_uploader("上传竞品数据 CSV", type=["csv"])
        experiment_file = st.file_uploader("上传匿名 A/B/问卷 CSV", type=["csv"])
        run_button = st.button("运行整套 Marketing OS", type="primary", use_container_width=True)
        st.divider()
        st.caption("默认使用 data/ 中的可复现实验样本。")

    paths = {
        "brand": DATA / "brand_profile.json",
        "reviews": DATA / "consumer_reviews.csv",
        "competitors": DATA / "competitors.csv",
        "experiment": DATA / "ab_test_anonymous.csv",
    }
    if run_button:
        # Uploaded files are staged in memory only for the current run; this
        # keeps the included sample files untouched and preserves provenance.
        if any((brand_file, review_file, competitor_file, experiment_file)) and not all((brand_file, review_file, competitor_file, experiment_file)):
            st.error("上传模式需要同时提供品牌、消费者、竞品和 A/B 四个文件。")
            return
        try:
            with tempfile.TemporaryDirectory(prefix="marketing-os-") as temp:
                staged = {}
                uploads = {"brand": brand_file, "reviews": review_file, "competitors": competitor_file, "experiment": experiment_file}
                for key, uploaded in uploads.items():
                    if uploaded is not None:
                        target = Path(temp) / uploaded.name
                        target.write_bytes(uploaded.getvalue())
                        staged[key] = target
                chosen = staged or paths
                result = run_os(chosen["brand"], chosen["reviews"], chosen["competitors"], chosen["experiment"], OUTPUT, DB)
            st.session_state["result"] = result
            st.success(f"运行完成：{result['run_id']}")
        except (DataValidationError, OSError, ValueError) as exc:
            st.error(f"运行失败：{exc}")

    result = st.session_state.get("result")
    if result is None and (OUTPUT / "marketing_os_run.json").exists():
        import json
        result = json.loads((OUTPUT / "marketing_os_run.json").read_text(encoding="utf-8"))
    if result is None:
        st.info("点击左侧按钮开始运行，或先查看默认样本的历史结果。")
        _table(history(DB, 10))
        return

    summary = result["summary"]
    cols = st.columns(5)
    for col, label, value in zip(cols, ["消费者样本", "平均评分", "首要痛点", "内容机会", "购买率提升"], [summary["sample_size"], result["consumer"]["average_rating"], summary["top_pain_point"], summary["top_opportunity"], f"{summary['ab_purchase_rate_uplift_pct']}%"]):
        col.metric(label, value)

    tabs = st.tabs(["品牌档案", "消费者洞察", "竞品情报", "内容机会", "Campaign Planner", "效果分析", "证据与下载", "历史记录"])
    with tabs[0]:
        st.json(result["brand"])
    with tabs[1]:
        _table(result["consumer"]["topic_ranking"])
        st.caption(result["consumer"]["evidence_boundary"])
    with tabs[2]:
        _table(result["competitors"]["ranking"])
        _table(result["competitors"]["gaps"])
    with tabs[3]:
        _table(result["content_opportunities"]["opportunities"])
        st.caption(result["content_opportunities"]["formula"])
    with tabs[4]:
        campaign = result["campaign"]
        st.subheader(campaign["theme"])
        st.write(campaign["goal"])
        _table(campaign["channels"])
        _table(campaign["kpis"])
        _table(campaign["human_review"]["checkpoints"])
    with tabs[5]:
        _table(result["experiment_effect"]["groups"])
        st.metric("点击率相对提升", f"{result['experiment_effect']['ctr_uplift_pct']}%")
        st.metric("购买率相对提升", f"{result['experiment_effect']['purchase_rate_uplift_pct']}%")
        st.info(result["experiment_effect"]["next_optimization"])
        st.caption("；".join(result["experiment_effect"]["limitations"]))
    with tabs[6]:
        st.json(result["evidence_ledger"])
        for file in ("marketing_os_run.json", "summary.json", "analysis_report.md", "content_opportunities.csv", "ab_group_results.csv"):
            path = OUTPUT / file
            if path.exists():
                st.download_button(f"下载 {file}", path.read_bytes(), file_name=file, key=file)
    with tabs[7]:
        _table(history(DB, 20))


if __name__ == "__main__":
    main()
