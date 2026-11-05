"""Experiment 7: a traceable, dependency-free AI marketing workflow.

The first six experiments produce small, reviewable files.  This module turns
those files into a stateful workflow for a campaign request.  Every step keeps
its input, output, source references, status and timing in the run record.  The
API client is deliberately local and deterministic so the classroom exercise
can demonstrate JSON contracts, retries and timeouts without requiring a key
or a network connection.

Run from the repository root::

    python src/marketing_workflow.py

The default request is ``给Campus Coffee设计一次新品推广``.  It writes a
workflow diagram, JSON schema, interface and error tables, an execution log,
and a draft campaign under ``experiments/experiment-7-ai-marketing-workflow``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = PROJECT_ROOT / "experiments" / "experiment-7-ai-marketing-workflow"
DEFAULT_OUTPUT_DIR = WORKFLOW_DIR / "outputs"
DEFAULT_LOG_PATH = WORKFLOW_DIR / "logs" / "workflow_run.jsonl"
DEFAULT_DOCS_DIR = WORKFLOW_DIR / "docs"
VERSION = "v0.7"
DEFAULT_REQUEST = "给Campus Coffee设计一次新品推广"

DEFAULT_SOURCES = {
    "consumer_pain": PROJECT_ROOT / "experiments" / "experiment-4-consumer-insight" / "outputs" / "pain_point_ranking.csv",
    "consumer_sentiment": PROJECT_ROOT / "experiments" / "experiment-4-consumer-insight" / "outputs" / "sentiment_distribution.csv",
    "competitor_threat": PROJECT_ROOT / "experiments" / "experiment-5-competitive-intelligence" / "outputs" / "threat_ranking.csv",
    "competitor_brands": PROJECT_ROOT / "experiments" / "experiment-5-competitive-intelligence" / "outputs" / "brand_comparison.csv",
    "content_matrix": PROJECT_ROOT / "experiments" / "experiment-6-content-gap-brand-voice" / "outputs" / "demand_content_matrix.csv",
    "brand_voice_skill": PROJECT_ROOT / "skills" / "brand_voice" / "SKILL.md",
}


class WorkflowError(Exception):
    """Base error for a recoverable or reportable workflow failure."""


class ValidationError(WorkflowError):
    """Raised when an API or step payload does not satisfy its contract."""


class ApiError(WorkflowError):
    """Raised after an API call exhausts its retry budget."""


class ApiTimeout(ApiError):
    """Raised after an API call exceeds the configured timeout."""


JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "campus-coffee-workflow-v0.7",
    "title": "AI Marketing Workflow Run",
    "type": "object",
    "required": ["version", "run_id", "request", "status", "steps", "campaign", "manual_review"],
    "properties": {
        "version": {"type": "string", "const": VERSION},
        "run_id": {"type": "string", "minLength": 1},
        "request": {"type": "string", "minLength": 1},
        "status": {"type": "string", "enum": ["completed", "failed"]},
        "steps": {"type": "object", "minProperties": 9},
        "campaign": {"type": "object", "required": ["campaign_id", "status", "theme", "channels", "kpis"]},
        "manual_review": {"type": "object", "required": ["required", "checkpoints"]},
    },
}

STEP_ORDER = (
    "brand_info",
    "consumer_insight",
    "competitor_analysis",
    "content_gap",
    "brand_voice",
    "target_consumer",
    "communication_theme",
    "channel_plan",
    "campaign",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")


def _read_csv(path: str | Path, required: Iterable[str]) -> list[dict[str, str]]:
    source = Path(path)
    if not source.is_file():
        raise WorkflowError(f"source file not found: {source}")
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = set(required) - fields
        if missing:
            raise ValidationError(f"{source.name} missing fields: {sorted(missing)}")
        return [dict(row) for row in reader]


def _read_text(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise WorkflowError(f"source file not found: {source}")
    return source.read_text(encoding="utf-8")


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _compact(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def schema_errors(value: Any, schema: dict[str, Any], path: str = "$", *, check_const: bool = True) -> list[str]:
    """Return human-readable validation errors for the small local JSON schema."""

    errors: list[str] = []
    expected = schema.get("type")
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if expected and not type_ok.get(expected, True):
        return [f"{path}: expected {expected}"]
    if check_const and "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}: missing required field {field!r}")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: expected at least {schema['minProperties']} properties")
        for field, field_schema in schema.get("properties", {}).items():
            if field in value:
                errors.extend(schema_errors(value[field], field_schema, f"{path}.{field}", check_const=check_const))
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]", check_const=check_const))
    return errors


def validate_payload(value: Any, schema: dict[str, Any] = JSON_SCHEMA) -> None:
    errors = schema_errors(value, schema)
    if errors:
        raise ValidationError("; ".join(errors))


class LocalAPIClient:
    """A local API adapter with the same timeout/retry semantics as a remote client."""

    def __init__(
        self,
        transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        *,
        timeout: float = 3.0,
        retries: int = 2,
        backoff: float = 0.05,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.transport = transport or self._default_transport
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.backoff = max(0.0, backoff)
        self.event_sink = event_sink

    @staticmethod
    def _default_transport(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        # The response is an acknowledgement. Analysis remains deterministic
        # and is performed by the step using local experiment artifacts.
        return {"ok": True, "endpoint": endpoint, "request_id": payload.get("request_id", "local")}

    def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink:
            self.event_sink(event)

    def call(self, endpoint: str, payload: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
        limit = self.timeout if timeout is None else timeout
        errors: list[str] = []
        for attempt in range(1, self.retries + 2):
            started = time.monotonic()
            self._emit({"event": "api_call", "endpoint": endpoint, "attempt": attempt, "status": "started", "timestamp": utc_now()})
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self.transport, endpoint, payload)
            try:
                response = future.result(timeout=limit)
                if not isinstance(response, dict):
                    raise ValidationError("API response must be a JSON object")
                self._emit({"event": "api_call", "endpoint": endpoint, "attempt": attempt, "status": "succeeded", "response": response, "elapsed_ms": round((time.monotonic() - started) * 1000, 2), "timestamp": utc_now()})
                return response
            except FutureTimeout:
                future.cancel()
                message = f"timeout after {limit:.3f}s"
                errors.append(message)
                self._emit({"event": "api_call", "endpoint": endpoint, "attempt": attempt, "status": "timeout", "error": message, "timestamp": utc_now()})
            except Exception as exc:  # transport errors are intentionally surfaced in the log
                message = f"{type(exc).__name__}: {exc}"
                errors.append(message)
                self._emit({"event": "api_call", "endpoint": endpoint, "attempt": attempt, "status": "failed", "error": message, "timestamp": utc_now()})
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            if attempt <= self.retries:
                time.sleep(self.backoff * attempt)
        if errors and all(error.startswith("timeout") for error in errors):
            raise ApiTimeout(f"{endpoint} failed after {len(errors)} attempt(s): {errors[-1]}")
        raise ApiError(f"{endpoint} failed after {len(errors)} attempt(s): {errors[-1] if errors else 'unknown error'}")


def _event_logger(events: list[dict[str, Any]]) -> Callable[[dict[str, Any]], None]:
    def sink(event: dict[str, Any]) -> None:
        events.append(dict(event))

    return sink


def _request_id(run_id: str, step: str) -> str:
    return f"{run_id}-{step}"


def _source_path(sources: dict[str, Path], key: str) -> str:
    return str(sources.get(key, DEFAULT_SOURCES[key]))


def _brand_info(request: str, sources: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    # The classroom prompt uses ``给Campus Coffee设计...``.  Capture the
    # complete name, including spaces, up to the action verb instead of
    # stopping at the first whitespace.
    match = re.search(r"(?:给|为)\s*(.+?)\s*(?:设计|策划|制定)", request)
    brand = match.group(1).strip() if match else "Campus Coffee"
    return ({
        "brand_name": brand,
        "category": "coffee",
        "launch_type": "new_product",
        "request": request,
        "objective": "在校园场景验证新品传播主题、渠道和转化路径",
        "source_scope": "user_request",
    }, ["user_request"])


def _consumer_insight(_: dict[str, Any], sources: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    pain = _read_csv(sources["consumer_pain"], {"rank", "topic", "count", "denominator", "share_pct"})
    sentiment = _read_csv(sources["consumer_sentiment"], {"sentiment", "count", "denominator", "share_pct"})
    top = sorted(pain, key=lambda row: int(row["rank"]))[:3]
    denominator = int(top[0]["denominator"]) if top else 0
    return ({
        "sample_size": denominator,
        "top_pain_points": [{"topic": row["topic"], "count": int(row["count"]), "share_pct": float(row["share_pct"])} for row in top],
        "sentiment": [{"label": row["sentiment"], "count": int(row["count"]), "share_pct": float(row["share_pct"])} for row in sentiment],
        "evidence_boundary": "实验4为咖啡评论模拟样本；比例描述样本，不代表全体校园消费者。",
        "source_files": [str(sources["consumer_pain"]), str(sources["consumer_sentiment"])],
    }, ["E4:pain_point_ranking.csv", "E4:sentiment_distribution.csv"])


def _competitor_analysis(_: dict[str, Any], sources: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    threats = _read_csv(sources["competitor_threat"], {"rank", "brand", "threat_index", "evidence_records"})
    brands = _read_csv(sources["competitor_brands"], {"brand", "avg_price", "avg_rating", "engagement"})
    leader = sorted(threats, key=lambda row: int(row["rank"]))[0] if threats else {}
    brand_rows = {row["brand"]: row for row in brands}
    leader_brand = leader.get("brand", "未识别")
    return ({
        "focal_brand": leader.get("focal_brand", "NovaPulse"),
        "top_rival": leader_brand,
        "threat_index": float(leader.get("threat_index", 0)),
        "rival_evidence_records": int(leader.get("evidence_records", 0)),
        "rival_snapshot": brand_rows.get(leader_brand, {}),
        "category_alignment": "not_aligned",
        "use_rule": "实验5是蓝牙降噪耳机样本，只用于演示竞争分析结构，不能作为咖啡竞品事实。",
        "source_files": [str(sources["competitor_threat"]), str(sources["competitor_brands"])],
    }, ["E5:threat_ranking.csv", "E5:brand_comparison.csv"])


def _content_gap(_: dict[str, Any], sources: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    rows = _read_csv(sources["content_matrix"], {"theme_id", "theme", "status", "opportunity_score", "category_fit", "consumer_importance_pct"})
    ranked = sorted(rows, key=lambda row: float(row["opportunity_score"] or 0), reverse=True)
    opportunities = [
        {
            "theme_id": row["theme_id"],
            "theme": row["theme"],
            "status": row["status"],
            "score": float(row["opportunity_score"]) if row["opportunity_score"] else None,
            "category_fit": row["category_fit"],
            "consumer_importance_pct": float(row["consumer_importance_pct"]) if row["consumer_importance_pct"] else None,
        }
        for row in ranked[:4]
    ]
    return ({
        "opportunities": opportunities,
        "selected_hypothesis": opportunities[0] if opportunities else None,
        "evidence_boundary": "实验6已明确标注咖啡与耳机类别不一致；跨类别价格信号只能形成假设，发布前需要校园咖啡自有数据验证。",
        "human_gate": "必须先审核类别匹配和证据边界，再进入投放文案。",
        "source_file": str(sources["content_matrix"]),
    }, ["E6:demand_content_matrix.csv"])


def _brand_voice(context: dict[str, Any], sources: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    skill_text = _read_text(sources["brand_voice_skill"])
    prohibited = [word for word in ("全网第一", "行业领先", "顶级", "彻底降噪", "零延迟", "百分百有效") if word in skill_text]
    return ({
        "voice": ["清楚", "克制", "具体", "以校园场景为中心"],
        "rules": ["先说用户决定，再给测试条件", "保留样本量、分母和证据来源", "把跨类别信号写成待验证假设", "用轻量邀请代替强迫式促销"],
        "prohibited_claims": prohibited or ["未经验证的绝对化表述"],
        "draft_line": f"{context['brand_info']['brand_name']}：上课前，先喝到对味的一杯。",
        "source_file": str(sources["brand_voice_skill"]),
    }, ["brand_voice/SKILL.md"])


def _target_consumer(context: dict[str, Any], _: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    insight = context["consumer_insight"]
    return ({
        "primary": "18—28岁的学生与校园教职工，常在上课、通勤或自习前购买咖啡",
        "decision": "希望在可接受价格内快速获得稳定口味的咖啡",
        "observed_signals": insight["top_pain_points"],
        "unvalidated_needs": ["具体新品口味偏好", "校园门店可接受价格", "高峰期真实等待时长"],
        "research_next": "先访谈5名目标用户，再用小流量A/B测试验证主题和优惠机制。",
    }, ["E4:pain_point_ranking.csv", "human_review:target_definition"])


def _communication_theme(context: dict[str, Any], _: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    brand = context["brand_info"]["brand_name"]
    return ({
        "theme": "上课前，先喝到对味的一杯",
        "promise": "用真实口味、价格和出杯时间信息，帮助校园用户做选择。",
        "content_pillars": ["口味试饮记录", "高峰期出杯时间实测", "学生可接受价格的小样本投票"],
        "claim_mode": "test_first",
        "draft_headlines": [
            f"{brand}新品试饮：上课前这一杯，口味和等待时间都写清楚",
            "先看实测，再决定今天喝哪杯",
            "校园高峰期，几分钟能拿到新品？",
        ],
        "evidence_boundary": "当前数据不能证明新品口味、价格或等待时间；以上内容是待执行的测试计划。",
    }, ["E4:pain_point_ranking.csv", "E6:demand_content_matrix.csv", "human_review:claim_gate"])


def _channel_plan(context: dict[str, Any], _: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    return ({
        "channels": [
            {"channel": "校园社群", "role": "收集试饮报名与价格反馈", "format": "问卷+群内投票"},
            {"channel": "小红书/短视频", "role": "展示口味与高峰期出杯实测", "format": "30秒竖屏实测"},
            {"channel": "门店二维码", "role": "承接新品试饮和优惠核销", "format": "桌卡/杯套二维码"},
        ],
        "sequence": ["招募试饮", "发布实测", "小范围优惠", "复盘并决定是否扩大投放"],
        "budget_rule": "先小流量验证，未通过人工审核和数据门槛不扩大预算。",
        "kpis": [
            {"name": "试饮报名率", "definition": "看到招募内容的用户中完成报名的比例", "target": "先建立基线"},
            {"name": "优惠核销率", "definition": "领取新品优惠的用户中完成核销的比例", "target": "A/B测试后设定"},
            {"name": "复购意向", "definition": "试饮后愿意在7天内再次购买的比例", "target": "访谈与问卷验证"},
        ],
        "manual_review": "渠道投放前由品牌方确认预算、校园合规和优惠规则。",
    }, ["human_review:channel_and_budget_gate"])


def _campaign(context: dict[str, Any], _: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    theme = context["communication_theme"]
    return ({
        "campaign_id": "CC-NEWPRODUCT-V07",
        "status": "draft_pending_human_review",
        "brand": context["brand_info"]["brand_name"],
        "objective": context["brand_info"]["objective"],
        "audience": context["target_consumer"]["primary"],
        "theme": theme["theme"],
        "content_pillars": theme["content_pillars"],
        "headlines": theme["draft_headlines"],
        "channels": context["channel_plan"]["channels"],
        "kpis": context["channel_plan"]["kpis"],
        "evidence_ledger": [
            {"claim": "配送/等待是样本中的首要痛点之一", "source": "E4:pain_point_ranking.csv", "boundary": "200条咖啡模拟评论"},
            {"claim": "价格信号可用于形成传播假设", "source": "E6:demand_content_matrix.csv", "boundary": "跨类别代理信号，不能证明耳机或校园新品需求"},
            {"claim": "竞品威胁分析已有结构化结果", "source": "E5:threat_ranking.csv", "boundary": "蓝牙耳机样本，不作为咖啡竞品结论"},
        ],
        "prohibited_claims": context["brand_voice"]["prohibited_claims"],
        "human_review": {
            "required": True,
            "checkpoints": [
                {"id": "claim_gate", "status": "pending", "owner": "品牌负责人", "check": "逐条核对文案与证据边界"},
                {"id": "pilot_gate", "status": "pending", "owner": "增长负责人", "check": "确认5人访谈、A/B测试和预算上限"},
                {"id": "publish_gate", "status": "pending", "owner": "门店/合规", "check": "确认校园场景、优惠和素材可发布"},
            ],
        },
    }, ["E4:pain_point_ranking.csv", "E5:threat_ranking.csv", "E6:demand_content_matrix.csv", "human_review:publish_gate"])


STEP_FUNCTIONS: dict[str, Callable[[dict[str, Any], dict[str, Path]], tuple[dict[str, Any], list[str]]]] = {
    "brand_info": _brand_info,  # type: ignore[assignment]
    "consumer_insight": _consumer_insight,
    "competitor_analysis": _competitor_analysis,
    "content_gap": _content_gap,
    "brand_voice": _brand_voice,
    "target_consumer": _target_consumer,
    "communication_theme": _communication_theme,
    "channel_plan": _channel_plan,
    "campaign": _campaign,
}


def _run_error_drills(
    timeout: float,
    retries: int,
    *,
    event_sink: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Exercise the four failure paths required by the lab brief."""
    drills: list[dict[str, Any]] = []

    calls = {"count": 0}

    def flaky(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("simulated upstream 503")
        return {"ok": True, "recovered": True}

    retry_client = LocalAPIClient(flaky, timeout=timeout, retries=max(2, retries), backoff=0.0, event_sink=event_sink)
    try:
        response = retry_client.call("debug/flaky", {})
        drills.append({"case": "API失败与重试", "status": "recovered", "detail": f"第{calls['count']}次调用成功: {response['recovered']}"})
    except ApiError as exc:
        drills.append({"case": "API失败与重试", "status": "failed", "detail": str(exc)})

    try:
        json.loads('{"broken":')
    except json.JSONDecodeError as exc:
        drills.append({"case": "JSON格式错误", "status": "handled", "detail": f"第{exc.lineno}行第{exc.colno}列: {exc.msg}"})

    try:
        validate_payload({"version": VERSION}, JSON_SCHEMA)
    except ValidationError as exc:
        drills.append({"case": "缺字段", "status": "handled", "detail": str(exc)})

    def slow(_: str, __: dict[str, Any]) -> dict[str, Any]:
        time.sleep(max(timeout * 4, 0.05))
        return {"ok": True}

    timeout_client = LocalAPIClient(slow, timeout=min(timeout, 0.02), retries=1, backoff=0.0, event_sink=event_sink)
    try:
        timeout_client.call("debug/slow", {})
        drills.append({"case": "超时", "status": "unexpected_success", "detail": "模拟接口未超时"})
    except ApiTimeout as exc:
        drills.append({"case": "超时", "status": "handled", "detail": str(exc)})
    return drills


def run_workflow(
    request: str = DEFAULT_REQUEST,
    *,
    output_dir: str | Path | None = None,
    log_path: str | Path | None = None,
    sources: dict[str, str | Path] | None = None,
    timeout: float = 3.0,
    retries: int = 2,
    include_debug: bool = True,
    api_client: LocalAPIClient | None = None,
) -> dict[str, Any]:
    """Run all nine stages and return the JSON-serializable run record."""

    run_id = "WF-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    source_map = {key: Path(value) for key, value in (sources or {}).items()}
    source_map = {key: source_map.get(key, Path(value)) for key, value in DEFAULT_SOURCES.items()}
    events: list[dict[str, Any]] = []
    client = api_client or LocalAPIClient(timeout=timeout, retries=retries, event_sink=_event_logger(events))
    if api_client is not None and api_client.event_sink is None:
        api_client.event_sink = _event_logger(events)
    state: dict[str, Any] = {
        "version": VERSION,
        "run_id": run_id,
        "request": request,
        "status": "running",
        "started_at": utc_now(),
        "steps": {},
        "evidence": [],
        "events": events,
        "manual_review": {"required": True, "checkpoints": []},
    }
    context: dict[str, Any] = {}
    for step in STEP_ORDER:
        started = time.monotonic()
        state["current_step"] = step
        events.append({"event": "step", "step": step, "status": "started", "timestamp": utc_now()})
        try:
            step_input: Any = request if step == "brand_info" else context.copy()
            api_response = client.call(f"workflow/{step}", {"request_id": _request_id(run_id, step), "step": step})
            function = STEP_FUNCTIONS[step]
            if step == "brand_info":
                output, evidence = function(request, source_map)  # type: ignore[arg-type]
            else:
                output, evidence = function(context, source_map)
            if not isinstance(output, dict):
                raise ValidationError(f"{step} output must be an object")
            context[step] = output
            state["steps"][step] = {
                "status": "completed",
                "input": step_input,
                "api_response": api_response,
                "output": output,
                "evidence_refs": evidence,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            }
            state["evidence"].extend({"step": step, "ref": ref} for ref in evidence)
            events.append({"event": "step", "step": step, "status": "completed", "timestamp": utc_now()})
        except Exception as exc:
            state["status"] = "failed"
            state["steps"][step] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            }
            events.append({"event": "step", "step": step, "status": "failed", "error": str(exc), "timestamp": utc_now()})
            break

    if state["status"] != "failed":
        state["campaign"] = context["campaign"]
        state["manual_review"] = context["campaign"]["human_review"]
        state["status"] = "completed"
    else:
        state["campaign"] = {}
    if include_debug:
        state["debug_drills"] = _run_error_drills(timeout, retries, event_sink=_event_logger(events))
    state["finished_at"] = utc_now()
    state.pop("current_step", None)
    if state["status"] == "completed":
        validate_payload(state)
    _write_artifacts(state, output_dir=output_dir, log_path=log_path)
    return state


def _write_artifacts(state: dict[str, Any], *, output_dir: str | Path | None, log_path: str | Path | None) -> None:
    output = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    log = Path(log_path) if log_path else (output.parent / "logs" / "workflow_run.jsonl")
    docs = output.parent / "docs"
    output.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)

    (output / "campaign_strategy.json").write_text(json.dumps(state, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    campaign = state.get("campaign", {})
    lines = [
        f"# {campaign.get('brand', 'Campus Coffee')} 新品推广 Campaign（{VERSION}）",
        "",
        f"- 状态：`{campaign.get('status', state['status'])}`",
        f"- 主题：{campaign.get('theme', '—')}",
        f"- 目标人群：{campaign.get('audience', '—')}",
        "",
        "## 内容方向",
    ]
    lines.extend(f"- {item}" for item in campaign.get("content_pillars", []))
    lines.extend(["", "## 标题候选"])
    lines.extend(f"- {item}" for item in campaign.get("headlines", []))
    lines.extend(["", "## 渠道与指标"])
    for channel in campaign.get("channels", []):
        lines.append(f"- {channel['channel']}：{channel['role']}（{channel['format']}）")
    for kpi in campaign.get("kpis", []):
        lines.append(f"- KPI｜{kpi['name']}：{kpi['definition']}；目标：{kpi['target']}")
    lines.extend(["", "## 人工审核点"])
    for checkpoint in campaign.get("human_review", {}).get("checkpoints", []):
        lines.append(f"- `{checkpoint['id']}`｜{checkpoint['owner']}：{checkpoint['check']}")
    lines.extend(["", "## 证据边界", "- 竞品和内容空白证据来自前序实验；咖啡与蓝牙耳机类别不一致，跨类别结论只作为待验证假设。", "- 发布前必须完成用户访谈、价格/口味/等待时间实测和小流量 A/B 测试。"])
    (output / "campaign_strategy.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    with log.open("w", encoding="utf-8") as handle:
        for event in state.get("events", []):
            handle.write(json.dumps(event, ensure_ascii=False, default=_json_default) + "\n")
        for drill in state.get("debug_drills", []):
            handle.write(json.dumps({"event": "debug_drill", **drill}, ensure_ascii=False) + "\n")
        handle.write(json.dumps({"event": "workflow", "status": state["status"], "run_id": state["run_id"], "timestamp": state.get("finished_at")}, ensure_ascii=False) + "\n")

    (docs / "json_schema.json").write_text(json.dumps(JSON_SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (docs / "workflow.mmd").write_text(WORKFLOW_DIAGRAM, encoding="utf-8")
    (docs / "api_interface.md").write_text(API_INTERFACE, encoding="utf-8")
    (docs / "error_handling.md").write_text(render_error_table(state.get("debug_drills", [])), encoding="utf-8")


def render_error_table(drills: list[dict[str, Any]]) -> str:
    rows = [
        "# 错误处理与 Debug 记录",
        "",
        "| 场景 | 处理 | 结果 |",
        "|---|---|---|",
        "| API 失败 | 指数退避重试，耗尽后抛出 `ApiError` | 演示记录见运行日志 |",
        "| JSON 错误 | 捕获 `JSONDecodeError`，阻止脏数据进入下一步 | 演示记录见运行日志 |",
        "| 缺字段 | 按 JSON Schema 校验并停在当前步骤 | 演示记录见运行日志 |",
        "| 超时 | 每次调用设置 timeout，重试后抛出 `ApiTimeout` | 演示记录见运行日志 |",
        "",
        "## 本次 Debug 演练",
        "",
        "| 场景 | 状态 | 详情 |",
        "|---|---|---|",
    ]
    for drill in drills:
        rows.append(f"| {drill.get('case', '')} | {drill.get('status', '')} | {_compact(str(drill.get('detail', ''))).replace('|', '/') } |")
    rows.append("")
    return "\n".join(rows)


WORKFLOW_DIAGRAM = """flowchart LR
    U[用户输入\n给Campus Coffee设计一次新品推广] --> B[品牌资料]
    B --> I[消费者洞察\n实验4]
    I --> C[竞争分析\n实验5]
    C --> G[Content Gap\n实验6]
    G --> V[Brand Voice\n技能规则]
    V --> T[目标消费者]
    T --> M[传播主题]
    M --> H[渠道计划]
    H --> P[Campaign策略]
    G -.人工审核：类别与证据边界.-> V
    P --> R{人工审核点}
    R -->|通过| D[小流量测试]
    R -->|退回| V
    subgraph API[API调用模块]
      X[JSON请求] --> Y[超时/重试]
      Y --> Z[JSON响应校验]
    end
    B -.-> X
    I -.-> X
    C -.-> X
    P -.-> X
"""


API_INTERFACE = """# API 调用模块与接口说明（v0.7）

`src/marketing_workflow.py` 中的 `LocalAPIClient` 模拟远程 API，保持和真实 HTTP 客户端相同的四个行为：JSON 请求、JSON 响应、超时、重试。默认不访问网络，方便复现实验。

| Endpoint | 请求字段 | 响应约束 | 用途 |
|---|---|---|---|
| `workflow/brand_info` | `request_id`, `step` | JSON object | 记录用户任务和品牌上下文 |
| `workflow/consumer_insight` | `request_id`, `step` | JSON object | 触发实验4读取与汇总 |
| `workflow/competitor_analysis` | `request_id`, `step` | JSON object | 触发实验5读取与汇总 |
| `workflow/content_gap` | `request_id`, `step` | JSON object | 触发实验6读取与证据边界检查 |
| `workflow/*` | `request_id`, `step` | JSON object | 其他工作流节点的状态确认 |

每个请求最多执行 `retries + 1` 次；单次调用超过 `timeout` 秒记为超时。响应必须是 JSON object，否则进入错误处理。每次请求会写入 `workflow_run.jsonl`，包括 endpoint、attempt、状态和时间戳。

真实服务接入时，只需替换 `LocalAPIClient.transport(endpoint, payload)`，保留相同的响应校验和日志字段。
"""


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Experiment 7 AI marketing workflow")
    parser.add_argument("--request", default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--log-path", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--no-debug", action="store_true", help="skip the intentional error-handling drills")
    args = parser.parse_args()
    result = run_workflow(
        args.request,
        output_dir=args.output_dir,
        log_path=args.log_path,
        timeout=args.timeout,
        retries=args.retries,
        include_debug=not args.no_debug,
    )
    print(json.dumps({
        "version": result["version"],
        "run_id": result["run_id"],
        "status": result["status"],
        "completed_steps": [name for name, step in result["steps"].items() if step["status"] == "completed"],
        "manual_review_required": result["manual_review"]["required"],
        "output_dir": str(args.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
