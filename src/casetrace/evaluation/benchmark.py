"""评估输入：读取并校验 qrels、数据集与主数据，产出可用于正式评估的 benchmark。

只回答“这份输入能否用于正式评估”，不排序、不计算指标。
标签的人工确认与源 Case 的语义审阅状态分开：源 Case 仍是 draft 不影响已确认 benchmark 生效。
任何检查失败都抛 ValueError，不降级为不相关、不静默跳过、不改写源文件。
qrels 中 `sources` 的相对路径以 base_dir 为解析基准（默认仓库根目录）。
本版沿用已确认的历史快照约定：全部历史 Case 在每条 Query 的 known_at 之前已完整可用；
校验只用模型中存在的日期字段，不声称已实现通用时间过滤。
"""

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path

from casetrace.data.dataset_model import CaseDetail
from casetrace.data.reference import ReferenceData
from casetrace.demo import check_source_records, load_validated_dataset

EXPECTED_QRELS_VERSION = "dev-qrels-v2"
EXPECTED_SPLIT = "development"
REQUIRED_REVIEW_STATUS = "human_confirmed"
# src/casetrace/evaluation/benchmark.py → 仓库根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class BenchmarkQuery:
    """一条评估 Query；检索只用 text，known_at 只用于时点检查。"""

    query_id: str
    text: str
    known_at: date


@dataclass(frozen=True)
class VerifiedSource:
    """qrels 记录的一份源文件，以及按文件原字节核对通过的哈希。"""

    name: str
    recorded_path: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class Benchmark:
    """已校验的评估输入；judgments 只用于评分，不能进入检索文本。"""

    qrels_path: Path
    qrels_sha256: str
    qrels_version: str
    confirmed_on: str
    split: str
    base_dir: Path
    dataset: VerifiedSource
    reference_file: VerifiedSource
    dataset_review_status: str
    records: dict
    reference: ReferenceData
    queries: list[BenchmarkQuery]
    judgments: dict[str, dict[str, int]]
    latest_detection: date

    @property
    def case_ids(self) -> list[str]:
        """语料中的 Case ID；排序后与 BM25Retriever 的索引顺序一致。"""
        return sorted(case.case_id for case in self.records["cases"])

    def relevant_case_ids(self, query_id: str) -> set[str]:
        """该 Query 在整份语料中的全部正例，供指标函数使用。"""
        return {case_id for case_id, label in self.judgments[query_id].items() if label == 1}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_object(path: Path, description: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{description} 的顶层必须是 JSON 对象")
    return payload


def _verify_source(base_dir: Path, name: str, entry: object) -> VerifiedSource:
    """按文件原字节核对一个 sources 条目；失败时指出文件、预期和实际值，不刷新记录。"""
    if not isinstance(entry, dict):
        raise ValueError(f"qrels | sources.{name} | 必须是含 path 与 sha256 的对象")
    recorded_path, expected = entry.get("path"), entry.get("sha256")
    if not isinstance(recorded_path, str) or not recorded_path.strip():
        raise ValueError(f"qrels | sources.{name} | path | 必须是非空字符串")
    if not isinstance(expected, str) or not expected.strip():
        raise ValueError(f"qrels | sources.{name} | sha256 | 必须是非空字符串")
    path = base_dir / recorded_path
    if not path.is_file():
        raise ValueError(f"qrels | sources.{name} | 文件不存在：{path}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(
            f"qrels | sources.{name} | {path} | SHA-256 不一致：记录 {expected}，实际 {actual}；"
            "源数据已改变，标签需要重新确认，不能直接刷新哈希"
        )
    return VerifiedSource(name=name, recorded_path=recorded_path, path=path, sha256=actual)


def _parse_queries(payload: dict) -> list[BenchmarkQuery]:
    rows = payload.get("queries")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset | queries | 必须是非空列表")
    queries = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Dataset | queries[{index}] | 必须是 JSON 对象")
        query_id = row.get("query_id")
        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError(f"Dataset | queries[{index}] | query_id | 必须是非空字符串")
        if query_id in seen:
            raise ValueError(f"CR-03 | Dataset | queries[{index}] | query_id {query_id!r} 重复")
        seen.add(query_id)
        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Dataset | Query[{query_id}] | text | 必须是非空字符串")
        recorded = row.get("known_at")
        try:
            known_at = date.fromisoformat(recorded) if isinstance(recorded, str) else None
        except ValueError:
            known_at = None
        if known_at is None:
            raise ValueError(f"Dataset | Query[{query_id}] | known_at | 必须是 YYYY-MM-DD 日期")
        queries.append(BenchmarkQuery(query_id=query_id, text=text, known_at=known_at))
    return queries


def _check_point_in_time(queries: list[BenchmarkQuery], details: list[CaseDetail]) -> date:
    """检查语料在每条 Query 的时点前已可用，返回语料中最晚的发现日期。"""
    if not details:
        raise ValueError("Dataset | details | 不能为空")
    for query in queries:
        for detail in details:
            if detail.detection_time > query.known_at:
                raise ValueError(
                    f"时点一致性 | Query[{query.query_id}] | CaseDetail[{detail.detail_id}] | "
                    f"detection_time {detail.detection_time.isoformat()} 晚于 "
                    f"known_at {query.known_at.isoformat()}；当前快照约定语料在该时点前完整可用，"
                    "本版不实现通用时间过滤"
                )
    return max(detail.detection_time for detail in details)


def _parse_judgments(
    payload: dict, query_ids: list[str], case_ids: list[str],
) -> dict[str, dict[str, int]]:
    rows = payload.get("judgments")
    if not isinstance(rows, list) or not rows:
        raise ValueError("qrels | judgments | 必须是非空列表")
    allowed_ids = {"query_id": set(query_ids), "case_id": set(case_ids)}
    labels: dict[str, dict[str, int]] = {query_id: {} for query_id in query_ids}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"qrels | judgments[{index}] | 必须是 JSON 对象")
        for field in ("query_id", "case_id"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"qrels | judgments[{index}] | {field} | 必须是非空字符串")
            if value not in allowed_ids[field]:
                raise ValueError(
                    f"qrels | judgments[{index}] | {field} {value!r} | 不在本次语料的范围内"
                )
        query_id, case_id = row["query_id"], row["case_id"]
        if case_id in labels[query_id]:
            raise ValueError(f"CR-03 | qrels | ({query_id}, {case_id}) | 配对重复")
        relevance = row.get("relevance")
        if type(relevance) is not int or relevance not in (0, 1):
            raise ValueError(
                f"qrels | ({query_id}, {case_id}) | relevance | 必须是整数 0 或 1；"
                f"未标注或 Ambiguous 不能用于正式评估，也不降级为不相关（实际 {relevance!r}）"
            )
        rationale = row.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"qrels | ({query_id}, {case_id}) | rationale | 必须是非空字符串")
        labels[query_id][case_id] = relevance
    missing = [f"({query_id}, {case_id})" for query_id in query_ids for case_id in case_ids
               if case_id not in labels[query_id]]
    if missing:
        raise ValueError(f"qrels | judgments | 缺少 {len(missing)} 个配对：" + "、".join(missing))
    return labels


def load_benchmark(qrels_path: Path, *, base_dir: Path | None = None) -> Benchmark:
    """读取并校验一份 benchmark；失败抛 ValueError，成功返回可评估的输入。

    base_dir 是 qrels 中相对来源路径的解析基准，默认仓库根目录，
    测试可用临时目录构造隔离的输入。
    """
    qrels_path = Path(qrels_path)
    base_dir = Path(PROJECT_ROOT if base_dir is None else base_dir)
    qrels = _read_json_object(qrels_path, "qrels")

    for field, expected in (("qrels_version", EXPECTED_QRELS_VERSION), ("split", EXPECTED_SPLIT)):
        actual = qrels.get(field)
        if actual != expected:
            raise ValueError(f"qrels | {field} | 期望 {expected}，实际 {actual!r}")
    if qrels.get("review_status") != REQUIRED_REVIEW_STATUS:
        raise ValueError(
            f"qrels | review_status | 正式评估要求 {REQUIRED_REVIEW_STATUS}，"
            f"实际 {qrels.get('review_status')!r}；未确认的标签只能作为草稿"
        )
    confirmed_on = qrels.get("confirmed_on")
    if not isinstance(confirmed_on, str) or not confirmed_on.strip():
        raise ValueError("qrels | confirmed_on | 用户确认日期必须是非空字符串")

    sources = qrels.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("qrels | sources | 必须是对象")
    dataset_source = _verify_source(base_dir, "dataset", sources.get("dataset"))
    reference_source = _verify_source(base_dir, "reference", sources.get("reference"))

    records, payload, reference = load_validated_dataset(dataset_source.path, reference_source.path)
    check_source_records(records, payload, reference)

    if payload.get("split") != EXPECTED_SPLIT:
        raise ValueError(f"Dataset | split | 期望 {EXPECTED_SPLIT}，实际 {payload.get('split')!r}")
    review_status = payload.get("review_status")
    if not isinstance(review_status, str) or not review_status.strip():
        raise ValueError("Dataset | review_status | 必须是非空字符串")

    queries = _parse_queries(payload)
    case_ids = sorted(case.case_id for case in records["cases"])
    latest_detection = _check_point_in_time(queries, records["details"])
    judgments = _parse_judgments(qrels, [query.query_id for query in queries], case_ids)

    return Benchmark(
        qrels_path=qrels_path,
        qrels_sha256=_sha256(qrels_path),
        qrels_version=qrels["qrels_version"],
        confirmed_on=confirmed_on,
        split=qrels["split"],
        base_dir=base_dir,
        dataset=dataset_source,
        reference_file=reference_source,
        dataset_review_status=review_status,
        records=records,
        reference=reference,
        queries=queries,
        judgments=judgments,
        latest_detection=latest_detection,
    )
