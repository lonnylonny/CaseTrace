"""M4-04 SD1：五条 dev-v3 Query 的真实调用与版本化结果。

用法：

    uv run python tmp/m4_04_run_all.py --check-only    # 只打印候选排名与 qrels 命中核对，不调用模型
    uv run python tmp/m4_04_run_all.py                 # 五条真实调用，保存到 results/m4/dev-v3-answer-v10/
    uv run python tmp/m4_04_run_all.py --query-id Q001 # 只跑一条，便于重试单条失败

产物（每 Query 一份）：
    results/m4/dev-v3-answer-v10/q00X.json     # 运行记录（复用 CLI 的 record schema）
    results/m4/dev-v3-answer-v10/q00X.cli.txt  # 终端文本输出

凭据只从 DEEPSEEK_API_KEY 读取，不写入产物；不改语料、qrels、标签或检索参数。
qrels 只在评估侧核对检索命中，绝不进入生成上下文。
"""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from casetrace.answer.cli import (
    build_model,
    format_answer_text,
    run_answer_question,
)
from casetrace.answer.context import build_evidence_context, prepare_answer_run

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
QRELS = ROOT / "data/evaluation/dev-v3/qrels.json"
OUTPUT_DIR = ROOT / "results/m4/dev-v3-answer-v10"
MODEL = "deepseek-flash"


def load_queries() -> dict[str, dict]:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    return {query["query_id"]: query for query in payload["queries"]}


def load_positives() -> dict[str, set[str]]:
    """从 qrels 取每条 Query 的 Relevant 正例，仅用于评估侧核对，不进入生成上下文。"""
    payload = json.loads(QRELS.read_text(encoding="utf-8"))
    positives: dict[str, set[str]] = {}
    for judgment in payload["judgments"]:
        positives.setdefault(judgment["query_id"], set())
        if judgment["relevance"] == 1:
            positives[judgment["query_id"]].add(judgment["case_id"])
    return positives


def ranking_for(query_id: str) -> list[str]:
    """用 R3 检索得到候选排名（Case ID 列表，顺序即名次）；不调用模型。"""
    query = load_queries()[query_id]
    run = prepare_answer_run(
        query["text"], date.fromisoformat(query["known_at"]),
        dataset_path=DATASET, reference_path=REFERENCE,
    )
    build_evidence_context(
        run.inputs.query, run.inputs.hits, run.inputs.records,
        run.inputs.reference, run.inputs.sources,
    )
    return [item["case_id"] for item in run.run_metadata["ranking"]]


def report_hits(query_ids: list[str]) -> None:
    """评估侧核对：候选排名 vs qrels 正例，输出命中/遗漏；不改任何数据。"""
    positives = load_positives()
    print("\n旧口径检索命中核对（qrels 仅评估侧使用，不进生成；不是新规则质量计分）：")
    print(f"{'Query':6} {'候选排名（前4）':24} {'命中正例':10} {'遗漏正例'}")
    for query_id in query_ids:
        ranking = ranking_for(query_id)[:4]
        pos = positives[query_id]
        hit = [case_id for case_id in ranking if case_id in pos]
        miss = sorted(pos - set(ranking))
        print(f"{query_id:6} {' > '.join(ranking):24} "
              f"{f'{len(hit)}/{len(pos)}':10} {', '.join(miss) or '—'}")


def ensure_targets_absent(query_ids: list[str], output_dir: Path) -> None:
    """全部目标先检查；任一已存在就停止，不花费模型调用、不覆盖失败记录。"""
    for query_id in query_ids:
        for suffix in ("json", "cli.txt"):
            target = output_dir / f"{query_id.lower()}.{suffix}"
            if target.exists():
                raise FileExistsError(f"已有产物不得覆盖：{target}；请使用新版本目录")


def run_one(query_id: str, output_dir: Path) -> int:
    ensure_targets_absent([query_id], output_dir)
    query = load_queries()[query_id]
    known_at = date.fromisoformat(query["known_at"])
    outcome = run_answer_question(
        query["text"], known_at, dataset_path=DATASET, reference_path=REFERENCE,
        model_factory=lambda: build_model(MODEL), query_id=query_id,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    low = query_id.lower()
    json_path = output_dir / f"{low}.json"
    cli_path = output_dir / f"{low}.cli.txt"
    # 排他创建同时防止检查后的竞态覆盖；写入失败也必须显式报错。
    with json_path.open("x", encoding="utf-8") as stream:
        json.dump(outcome.record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with cli_path.open("x", encoding="utf-8") as stream:
        stream.write(format_answer_text(outcome))
    response = outcome.record["response"]
    citations = outcome.record["citations"]
    usage = response.get("usage") or {}
    print(f"{query_id}: status={outcome.status} model={response.get('model')} "
          f"elapsed={response.get('elapsed_seconds'):.2f}s "
          f"tokens={usage.get('total_tokens')} "
          f"citations_checked={citations.get('checked')} issues={citations.get('issue_count')}")
    if outcome.status not in ("ok", "no_hits"):
        print(f"  -> 失败详情：{outcome.message}", file=sys.stderr)
    return outcome.exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="M4-04 五条真实调用与检索命中核对")
    parser.add_argument("--check-only", action="store_true", help="只打印候选排名与命中核对，不调用模型")
    parser.add_argument("--query-id", default=None, help="只处理指定 Query（如 Q001）")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="产物目录")
    args = parser.parse_args()

    query_ids = [args.query_id] if args.query_id else list(load_queries())
    missing = [qid for qid in query_ids if qid not in load_queries()]
    if missing:
        print(f"未知 Query：{missing}；可选：{list(load_queries())}", file=sys.stderr)
        return 2

    if args.check_only:
        report_hits(query_ids)
        return 0

    output_dir = Path(args.output_dir)
    try:
        ensure_targets_absent(query_ids, output_dir)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    exit_code = 0
    for query_id in query_ids:
        try:
            code = run_one(query_id, output_dir)
            if code:
                exit_code = code
        except Exception as exc:  # 单条失败不中断其余，保留失败证据后继续
            print(f"{query_id}: 未捕获异常 {type(exc).__name__}: {exc}", file=sys.stderr)
            exit_code = 1
    report_hits(query_ids)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
