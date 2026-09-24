"""评估运行器：在已校验 benchmark 上建一次索引，逐 Query 排序并计算单条 Query 指标。

只使用检索产生的事实（Case ID、名次、分数、命中词项）。
标签和理由只参与评分，不进入历史检索文本或 Query 文本。
aggregate 负责跨 Query 汇总：各指标对参与 Query 等权平均，无正例 Query 只排除该 Query 不适用的指标。
run_evaluation 在一次调用内完成校验、建索引、计分、汇总和可复现报告，并记录建索引与逐 Query 计分的耗时观测值；
耗时附带测量边界，且只描述本次运行，不参与确定性比较。
write_report 负责把报告落盘，先写临时文件再原子替换，失败不留半份结果。
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter

from casetrace.demo import build_documents
from casetrace.evaluation.benchmark import (
    PROJECT_ROOT,
    Benchmark,
    BenchmarkQuery,
    load_benchmark,
)
from casetrace.evaluation.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)
from casetrace.retrieval.base import Retriever
from casetrace.retrieval.bm25 import BM25Retriever
from casetrace.retrieval.embedding import EmbeddingRetriever

# M2 固定的评估口径：逐 Query 报告 K=1/3/4 的 Recall、Precision、nDCG，RR 只用 K=4。
METRIC_KS = (1, 3, 4)
RECIPROCAL_RANK_K = 4

# 逐 Query 分数键与跨 Query 汇总键；按 M2 口径，RR@4 的均值命名为 MRR@4。
RR_KEY = f"rr@{RECIPROCAL_RANK_K}"
MRR_KEY = f"mrr@{RECIPROCAL_RANK_K}"
_PER_QUERY_METRIC_KEYS = tuple(
    f"{name}@{k}" for name in ("recall", "precision", "ndcg") for k in METRIC_KS
)
SCORE_KEYS = _PER_QUERY_METRIC_KEYS + (RR_KEY,)
SUMMARY_METRIC_KEYS = _PER_QUERY_METRIC_KEYS + (MRR_KEY,)
# 目前唯一会出现的排除原因：该 Query 没有正例，指标不适用。
NO_RELEVANT_REASON = "no_relevant_case"

# 结果文件的格式版本与固定口径说明；口径文字只描述已实现的行为，不额外承诺能力。
# v2 在 v1 的基础上增加顶层 timing；其余字段的名称、数量与口径不变。
RESULT_SCHEMA_VERSION = "evaluation-result-v2"
HISTORY_SNAPSHOT = (
    "本版沿用已确认的历史快照约定：全部历史 Case 在每条 Query 的 known_at 之前已结案并完整可用；"
    "未实现通用时间过滤，时点检查只用模型中存在的日期字段。"
)
NO_RELEVANT_POLICY = (
    "无正例 Query 单列：Recall / nDCG / RR@4 为 None 并从各自均值中排除，Precision 的 0.0 "
    "按函数口径纳入其均值；每个指标分别记录参与的 Query 与排除原因，没有可参与 Query 时汇总为 None。"
)
METRIC_DEFINITIONS = {
    "recall@k": "前 k 条中的相关 Case 数 / 该 Query 的全部正例数；返回不足 k 条用实际条目；无正例为 None。",
    "precision@k": "前 k 条中的相关 Case 数 / k；返回不足 k 条时分母仍为 k；无正例为 0.0。",
    "ndcg@k": "二值 gain，按原排名累加 1/log2(rank+1)；IDCG 用第 1 至 min(k, 正例数) 名；无正例为 None。",
    "rr@4": "前 4 条中首个相关结果的 1/rank；前 4 条无命中为 0.0；无正例为 None。",
    "mrr@4": "逐 Query rr@4 对参与 Query 的等权平均；没有参与 Query 时为 None。",
}
# 耗时的测量边界与比较口径：耗时随机器、缓存与并发环境变化，只描述本次运行。
TIMING_BOUNDARIES = (
    "index_build：覆盖历史检索文本构建与检索器构造（建索引）；不含输入校验、逐 Query 计分与报告组装。"
    "需要编码的方法（embedding）还包含模型加载与文档编码，命中缓存时只包含缓存读取；"
    "细分见顶层 timing.method_details。",
    "per_query：每条 Query 一次，覆盖该 Query 的检索、返回 ID 守卫与指标计算（qrels 只在此步进场）；"
    "按 Query 顺序逐条计分，不并发。",
    "total：从本次 run_evaluation 进入计到跨 Query 汇总完成；覆盖输入校验、建索引、逐 Query 计分与汇总，"
    "不含复现字段的 git 查询与文件哈希、写文件与终端输出。",
)
TIMING_COMPARISON_NOTE = (
    "耗时与 generated_at 只描述本次运行，不参与确定性比较：比较排名、分数与指标时必须忽略这两个字段。"
    "单次读数不足以评价方法效率；同版本方法比较耗时需固定硬件、冷启动与缓存条件并重复测量。"
)
# 覆盖 CLI → 数据读取/校验 → 检索/评分的执行源码；未提交的数据模块也属于运行版本。
# 数据文件哈希来自已校验的 benchmark，不在这里重复计算。
REPRODUCIBILITY_SOURCE_FILES = (
    "src/casetrace/__init__.py",
    "src/casetrace/data/constants.py",
    "src/casetrace/data/dataset_model.py",
    "src/casetrace/data/reference.py",
    "src/casetrace/data/validators.py",
    "src/casetrace/evaluation/runner.py",
    "src/casetrace/evaluation/benchmark.py",
    "src/casetrace/evaluation/metrics.py",
    "src/casetrace/demo.py",
    "src/casetrace/retrieval/base.py",
    "src/casetrace/retrieval/bm25.py",
    "src/casetrace/retrieval/embedding.py",
    "pyproject.toml",
    "uv.lock",
)


@dataclass(frozen=True)
class RankedCase:
    """一条 Query 的一个排名条目；名次从 1 开始、连续，与检索返回顺序一致。"""

    rank: int
    case_id: str
    score: float
    # None 表示所用检索方法不提供命中词项信息；评估器不替它编造词项。
    matched_terms: list[str] | None


@dataclass(frozen=True)
class QueryEvaluation:
    """一条 Query 的评估结果；scores 为 None 表示该指标因无正例而不适用。"""

    query_id: str
    query_text: str
    known_at: str
    relevant_case_ids: list[str]
    ranked: list[RankedCase]
    scores: dict[str, float | None]


@dataclass(frozen=True)
class ExcludedQuery:
    """一个指标未纳入均值的 Query 及其原因。"""

    query_id: str
    reason: str


@dataclass(frozen=True)
class MetricSummary:
    """一个指标的跨 Query 汇总；value 为 None 表示没有可参与的 Query。"""

    value: float | None
    included_query_ids: list[str]
    excluded: list[ExcludedQuery]


@dataclass(frozen=True)
class EvaluationSummary:
    """整份 benchmark 的汇总；各指标的分母差异由参与列表与排除列表体现。"""

    query_count: int
    no_relevant_query_ids: list[str]
    metrics: dict[str, MetricSummary]


# 可选检索方法：方法名 → 构造函数（输入 case_id → 历史检索文本）。
# 方法名是 CLI 与报告使用的稳定标识；新增方法只在这里加一行，不改计分、汇总或落盘。
DEFAULT_METHOD = "bm25"
RETRIEVER_FACTORIES: dict[str, Callable[[dict[str, str]], Retriever]] = {
    "bm25": BM25Retriever,
    "embedding": EmbeddingRetriever,
}


def build_retriever(benchmark: Benchmark, *, method: str = DEFAULT_METHOD) -> Retriever:
    """按方法名建一次检索索引并返回公共契约对象。

    文档只来自历史记录，标签、理由与审查元数据不参与；未知方法在这里明确报错，
    不回退到默认方法，调用方不会拿到"以为是自己选的方法"的结果。
    """
    factory = RETRIEVER_FACTORIES.get(method)
    if factory is None:
        available = "、".join(sorted(RETRIEVER_FACTORIES))
        raise ValueError(f"未实现的检索方法：{method!r}；当前可用：{available}")
    documents = build_documents(benchmark.records, benchmark.reference)
    if sorted(documents) != benchmark.case_ids:
        raise ValueError(
            f"检索语料与已校验语料不一致：文档 {sorted(documents)}，语料 {benchmark.case_ids}"
        )
    return factory(documents)


def rank_query(
    benchmark: Benchmark, retriever: Retriever, query: BenchmarkQuery,
) -> list[RankedCase]:
    """按 Query 文本排名；请求范围覆盖整个语料，超出语料或重复的返回 ID 直接报错。

    检索没有返回的 Case 不补分数、不补名次，排名长度即实际返回条数。
    """
    hits = retriever.search(query.text, top_k=len(benchmark.case_ids))
    case_ids = [hit.case_id for hit in hits]
    unknown = sorted(set(case_ids) - set(benchmark.case_ids))
    if unknown:
        raise ValueError(
            f"检索结果 | Query[{query.query_id}] | 返回了语料之外的 Case：{unknown}；"
            "排名只能包含已校验语料中的 Case"
        )
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"检索结果 | Query[{query.query_id}] | 返回了重复的 Case ID：{case_ids}")
    return [
        RankedCase(rank=rank, case_id=hit.case_id, score=hit.score, matched_terms=hit.matched_terms)
        for rank, hit in enumerate(hits, start=1)
    ]


def evaluate_query(
    benchmark: Benchmark, retriever: Retriever, query: BenchmarkQuery,
) -> QueryEvaluation:
    """一条 Query 的数据流：检索 → 校验排名 → 取该 Query 的正例 → 逐 K 计分。"""
    ranked = rank_query(benchmark, retriever, query)
    relevant_case_ids = benchmark.relevant_case_ids(query.query_id)
    ranked_case_ids = [item.case_id for item in ranked]

    scores: dict[str, float | None] = {}
    for k in METRIC_KS:
        scores[f"recall@{k}"] = recall_at_k(ranked_case_ids, relevant_case_ids, k)
        scores[f"precision@{k}"] = precision_at_k(ranked_case_ids, relevant_case_ids, k)
        scores[f"ndcg@{k}"] = ndcg_at_k(ranked_case_ids, relevant_case_ids, k)
    scores[RR_KEY] = reciprocal_rank_at_k(
        ranked_case_ids, relevant_case_ids, RECIPROCAL_RANK_K
    )

    return QueryEvaluation(
        query_id=query.query_id,
        query_text=query.text,
        known_at=query.known_at.isoformat(),
        relevant_case_ids=sorted(relevant_case_ids),
        ranked=ranked,
        scores=scores,
    )


def aggregate(evaluations: list[QueryEvaluation]) -> EvaluationSummary:
    """把逐 Query 分数汇总为跨 Query 读数：各指标对参与 Query 等权平均。

    无正例 Query 的 Recall / RR / nDCG 为 None（指标不适用），从各自均值中排除，
    并连同原因记入 excluded；Precision 按指标函数口径为 0.0，纳入其均值。
    没有任何可参与 Query 时该指标汇总为 None，不做除零、也不写成 0。
    逐 Query 的 RR@4 平均后命名为 MRR@4，与单条 Query 的排名倒数区分。
    分数为 None 但该 Query 有正例说明口径不一致，直接报错而不是静默少算一个分母。
    """
    query_ids = [evaluation.query_id for evaluation in evaluations]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError(f"汇总 | 输入包含重复的 Query ID：{query_ids}；重复会把同一条 Query 计两次")

    for evaluation in evaluations:
        actual = set(evaluation.scores)
        if actual != set(SCORE_KEYS):
            raise ValueError(
                f"汇总 | Query[{evaluation.query_id}] | 逐 Query 分数键与 M2 口径不符："
                f"期望 {sorted(SCORE_KEYS)}，实际 {sorted(actual)}"
            )

    metrics: dict[str, MetricSummary] = {}
    for summary_key in SUMMARY_METRIC_KEYS:
        score_key = RR_KEY if summary_key == MRR_KEY else summary_key
        included_query_ids: list[str] = []
        excluded: list[ExcludedQuery] = []
        values: list[float] = []
        for evaluation in evaluations:
            score = evaluation.scores[score_key]
            if score is None:
                if evaluation.relevant_case_ids:
                    raise ValueError(
                        f"汇总 | Query[{evaluation.query_id}] | {score_key} 为 None，"
                        "但该 Query 有正例；指标口径不一致"
                    )
                excluded.append(ExcludedQuery(evaluation.query_id, NO_RELEVANT_REASON))
                continue
            included_query_ids.append(evaluation.query_id)
            values.append(score)
        metrics[summary_key] = MetricSummary(
            value=sum(values) / len(values) if values else None,
            included_query_ids=included_query_ids,
            excluded=excluded,
        )

    return EvaluationSummary(
        query_count=len(evaluations),
        no_relevant_query_ids=[
            evaluation.query_id for evaluation in evaluations if not evaluation.relevant_case_ids
        ],
        metrics=metrics,
    )


def _relative(path: Path, base: Path) -> str:
    """报告里尽量使用相对路径；不在基准目录下时退回原路径，便于定位。"""
    try:
        return Path(os.path.relpath(path, base)).as_posix()
    except ValueError:
        return str(path)


def _file_sha256(path: Path) -> str | None:
    """代码或配置文件的 SHA-256；文件缺失时记 None，不假装已核对。"""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_versions(names: tuple[str, ...]) -> dict[str, str | None]:
    """记录实际安装的依赖版本；未安装时记 None，不猜测。"""
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def _git_state() -> tuple[str | None, list[str]]:
    """当前 HEAD 与工作区改动路径；git 不可用时返回 None 和空列表。"""
    def run(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        ).stdout

    try:
        head = run("rev-parse", "HEAD").strip()
        status = run("status", "--porcelain")
    except (OSError, subprocess.CalledProcessError):
        return None, []
    paths = sorted({line[3:].strip() for line in status.splitlines() if len(line) > 3})
    return head, paths


def _benchmark_document(benchmark: Benchmark) -> dict:
    """报告中的输入部分：已校验的版本、来源与实际哈希。"""
    return {
        "qrels_path": _relative(benchmark.qrels_path, benchmark.base_dir),
        "qrels_version": benchmark.qrels_version,
        "qrels_sha256": benchmark.qrels_sha256,
        "confirmed_on": benchmark.confirmed_on,
        "split": benchmark.split,
        "dataset": {"path": benchmark.dataset.recorded_path, "sha256": benchmark.dataset.sha256},
        "reference": {
            "path": benchmark.reference_file.recorded_path,
            "sha256": benchmark.reference_file.sha256,
        },
        "dataset_review_status": benchmark.dataset_review_status,
        "latest_detection": benchmark.latest_detection.isoformat(),
        "history_snapshot": HISTORY_SNAPSHOT,
    }


def _retrieval_document(benchmark: Benchmark, retriever: Retriever) -> dict:
    """报告中的检索部分：方法自己声明的元数据 + 评估器负责的语料范围。

    方法元数据来自 retriever.describe()，评估器不再读具体实现的内部对象；
    键的先后顺序不代表语义，字段内容由各方法自行声明。
    """
    return {
        **retriever.describe(),
        "document_builder": "casetrace.demo.build_documents",
        "corpus_size": len(benchmark.case_ids),
        "requested_top_k": len(benchmark.case_ids),
    }


def _run_details(retriever: Retriever) -> dict | None:
    """方法可选提供的本次运行观测值（耗时、缓存状态）；未提供时记 None，不编造字段。"""
    provider = getattr(retriever, "run_details", None)
    if provider is None:
        return None
    details = provider()
    return details if isinstance(details, dict) else None


def _timing_document(
    index_build_seconds: float,
    per_query_seconds: list[tuple[str, float]],
    total_seconds: float,
    method_details: dict | None = None,
) -> dict:
    """报告中的耗时部分：本次运行的观测秒数 + 测量边界。

    数值来自 time.perf_counter（单调时钟），不参与确定性比较；边界文字说明每个数字包住了哪一步，
    避免把"耗时"当成跨机器、跨缓存条件可比的效率结论。
    方法自己提供的 run_details()（存在时）原样记在 method_details，同样不参与比较。
    """
    document = {
        "unit": "seconds",
        "clock": "time.perf_counter",
        "index_build_seconds": index_build_seconds,
        "per_query": [
            {"query_id": query_id, "seconds": seconds}
            for query_id, seconds in per_query_seconds
        ],
        "queries_total_seconds": sum(seconds for _, seconds in per_query_seconds),
        "total_seconds": total_seconds,
        "boundaries": list(TIMING_BOUNDARIES),
        "comparison_note": TIMING_COMPARISON_NOTE,
    }
    if method_details is not None:
        document["method_details"] = method_details
    return document


def _metrics_document() -> dict:
    """报告中的指标部分：K、公式口径与特殊样本处理。"""
    return {
        "ks": list(METRIC_KS),
        "reciprocal_rank_k": RECIPROCAL_RANK_K,
        "summary_metric_keys": list(SUMMARY_METRIC_KEYS),
        "definitions": dict(METRIC_DEFINITIONS),
        "no_relevant_policy": NO_RELEVANT_POLICY,
        "comparison_note": "各方法必须在同一 Corpus、Query、已确认 qrels 与指标口径下比较；数据或标注变化后整体重跑。",
    }


def _reproducibility_document() -> dict:
    """报告的复现部分：代码、依赖与工作区状态；不包含可用作排名比较的字段。"""
    head, changed_paths = _git_state()
    notes = [
        "工作区未提交：仅 HEAD 不足以复现，source_files 与 uv.lock 的 SHA-256 是本次实际使用的代码与依赖记录。",
        "generated_at 只说明记录生成时间，不能作为排名或分数是否可重复的比较字段。",
    ]
    if head is None:
        notes.append("无法读取 git 状态（git 不可用或不在仓库中），工作区是否干净未知。")
    return {
        "python": platform.python_version(),
        "packages": _package_versions(
            ("casetrace", "rank-bm25", "openpyxl", "numpy",
             "sentence-transformers", "transformers", "torch"),
        ),
        "git_head": head,
        "git_dirty": bool(changed_paths),
        "git_status_paths": changed_paths,
        "source_files": {
            name: _file_sha256(PROJECT_ROOT / name) for name in REPRODUCIBILITY_SOURCE_FILES
        },
        "notes": notes,
    }


def run_evaluation(
    qrels_path: Path, *, base_dir: Path | None = None, method: str = DEFAULT_METHOD,
) -> dict:
    """完整评估入口：校验输入 → 按方法建一次索引 → 逐 Query 计分 → 汇总 → 可复现报告。

    返回可直接 json.dumps 的字典；不写文件、不打印，保存与展示由调用方负责。
    逐 Query 排名与分数来自 evaluate_query，汇总来自 aggregate，口径不在这里另算一遍。
    方法不认识时在写任何结果之前报错，调用方不会留下半份报告。
    耗时只记录本次运行的观测值并附边界说明，不参与排名、分数与指标的比较。
    """
    started = perf_counter()
    benchmark = load_benchmark(qrels_path, base_dir=base_dir)
    build_started = perf_counter()
    retriever = build_retriever(benchmark, method=method)
    index_build_seconds = perf_counter() - build_started
    evaluations: list[QueryEvaluation] = []
    per_query_seconds: list[tuple[str, float]] = []
    for query in benchmark.queries:
        query_started = perf_counter()
        evaluations.append(evaluate_query(benchmark, retriever, query))
        per_query_seconds.append((query.query_id, perf_counter() - query_started))
    summary = aggregate(evaluations)
    total_seconds = perf_counter() - started
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "benchmark": _benchmark_document(benchmark),
        "retrieval": _retrieval_document(benchmark, retriever),
        "timing": _timing_document(
            index_build_seconds, per_query_seconds, total_seconds, _run_details(retriever),
        ),
        "metrics": _metrics_document(),
        "queries": [asdict(evaluation) for evaluation in evaluations],
        "summary": asdict(summary),
        "reproducibility": _reproducibility_document(),
    }


def write_report(report: dict, output_path: Path) -> Path:
    """把报告写成 JSON：先写同目录临时文件再原子替换，失败时不留下半份结果。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output_path.parent,
        prefix=f"{output_path.name}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, output_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return output_path
