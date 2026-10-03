"""M4-02 SD3：一条真实 dev-v3 Query 的生成运行记录与证据移除对照。

用法：

    uv run python tmp/m4_02_generate.py --check-only                 # 只检查输入，不调用模型
    uv run python tmp/m4_02_generate.py                             # 正常上下文，真实调用一次
    uv run python tmp/m4_02_generate.py --drop-checkpoint C001:E2    # 移除一项支持证据后对照

产物：results/m4/m4-02-<query_id>[-drop-<case>-<checkpoint>].json
凭据只从 DEEPSEEK_API_KEY 读取，不写入产物；不改语料、qrels、标签或检索参数。
本脚本只是运行与记录工具，不是 CLI（CLI 属 M4-03），也不替代人工审阅回答。
"""

import argparse
from dataclasses import asdict, replace
from datetime import date
import json
from pathlib import Path
import sys

from casetrace.answer.context import (
    build_evidence_context,
    context_to_payload,
    prepare_answer_run,
)
from casetrace.answer.generation import generate_grounded_answer
from casetrace.answer.model import DeepSeekChatModel, ModelError
from casetrace.answer.prompt import render_system_prompt

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
OUTPUT_DIR = ROOT / "results/m4"


class RecordingModel:
    """记录实际发送的 messages，再转发给真实模型；只为运行记录，不改变调用行为。"""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.model_id = inner.model_id
        self.sent_messages: list[dict] = []

    def complete(self, messages, *, max_tokens=None, temperature=None):
        self.sent_messages = [
            {"role": item.role, "content": item.content} for item in messages
        ]
        return self._inner.complete(messages, max_tokens=max_tokens, temperature=temperature)


def load_query(query_id: str) -> dict:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    for query in payload["queries"]:
        if query["query_id"] == query_id:
            return query
    raise ValueError(
        f"语料中没有 Query {query_id}；可选：{[q['query_id'] for q in payload['queries']]}"
    )


def drop_checkpoint(context, case_id: str, checkpoint_id: str):
    """隔离副本：移除指定 Case 的一项检查结果；找不到就明确失败，不静默改数据。"""

    for index, case in enumerate(context.cases):
        if case.case_id != case_id:
            continue
        kept = [item for item in case.evidences if item.checkpoint_id != checkpoint_id]
        if len(kept) == len(case.evidences):
            raise ValueError(
                f"Case {case_id} 没有检查项 {checkpoint_id}；"
                f"实际有：{[item.checkpoint_id for item in case.evidences]}"
            )
        cases = list(context.cases)
        cases[index] = replace(case, evidences=kept)
        return replace(context, cases=cases)
    raise ValueError(
        f"上下文中没有 Case {case_id}；实际有：{[case.case_id for case in context.cases]}"
    )


def build_record(query: dict, run, context, result, recorder, dropped: str | None) -> dict:
    """可核对的运行记录：输入、实际发送内容、回答与运行身份；凭据不入产物。"""

    request_model = recorder._inner
    return {
        "record_version": "m4-02-sd3-run-1",
        "run": {
            "query_id": query["query_id"],
            "query": run.inputs.query,
            "known_at": run.inputs.known_at.isoformat(),
            "prompt_version": result.prompt_version,
            "request": {
                "model_alias": recorder.model_id,
                "max_tokens": getattr(request_model, "max_tokens", None),
                "temperature": getattr(request_model, "temperature", None),
                "response_format": "json_object",
                "thinking": "disabled",
            },
            "response": {
                "model": result.model_id,
                "called_model": result.called_model,
                "elapsed_seconds": round(result.elapsed_seconds, 3),
                "usage": result.usage.to_dict(),
            },
            "dropped_checkpoint": dropped,
        },
        "snapshot": run.run_metadata["snapshot"],
        "retrieval": run.run_metadata["retrieval"],
        "ranking": run.run_metadata["ranking"],
        "sent_messages": recorder.sent_messages,
        "context": context_to_payload(context),
        "answer_text": result.raw_response,
        "answer_parsed": asdict(result.answer),
        "limits": list(run.run_metadata["notes"]) + [
            "本记录是一次开发集观察，不是 Ground Truth，也不构成泛化结论。",
            "凭据不在产物中；运行身份以响应返回的 model 字段为准。",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="M4-02 SD3 真实生成与证据移除对照")
    parser.add_argument("--query-id", default="Q005",
                        help="dev-v3 Query ID（默认 Q005，含否定条件）")
    parser.add_argument("--drop-checkpoint", default=None,
                        help="证据移除对照：形如 C001:E2，移除该 Case 的这条检查结果")
    parser.add_argument("--check-only", action="store_true",
                        help="只检查输入与上下文，不调用模型、不写记录")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="产物目录")
    args = parser.parse_args()

    try:
        query = load_query(args.query_id)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    run = prepare_answer_run(
        query["text"], date.fromisoformat(query["known_at"]),
        dataset_path=DATASET, reference_path=REFERENCE,
    )
    context = build_evidence_context(
        run.inputs.query, run.inputs.hits, run.inputs.records,
        run.inputs.reference, run.inputs.sources,
    )
    dropped = None
    if args.drop_checkpoint:
        case_id, _, checkpoint_id = args.drop_checkpoint.partition(":")
        if not checkpoint_id:
            print("--drop-checkpoint 需要 CASE:CHECKPOINT 形式，例如 C001:E2", file=sys.stderr)
            return 2
        try:
            context = drop_checkpoint(context, case_id, checkpoint_id)
        except ValueError as exc:
            print(f"对照设置无效：{exc}", file=sys.stderr)
            return 2
        dropped = args.drop_checkpoint

    print(f"Query {query['query_id']}（{run.inputs.known_at.isoformat()}）：{run.inputs.query}")
    print("候选排名：", [(item["rank"], item["case_id"]) for item in run.run_metadata["ranking"]])
    print("上下文 Case：", [case.case_id for case in context.cases])
    print("检查项：", [item.checkpoint_id for case in context.cases for item in case.evidences])
    print(f"system 提示 {len(render_system_prompt())} 字符｜证据 JSON "
          f"{len(json.dumps(context_to_payload(context), ensure_ascii=False))} 字符")
    if dropped:
        print("对照设置：已移除", dropped)
    if args.check_only:
        print("--check-only：未调用模型，未写记录。")
        return 0

    try:
        model = RecordingModel(DeepSeekChatModel())
        result = generate_grounded_answer(run.inputs.query, context, model)
    except ModelError as exc:
        print(f"生成未完成：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    suffix = f"-drop-{dropped.replace(':', '-')}" if dropped else ""
    output = Path(args.output_dir) / f"m4-02-{query['query_id'].lower()}{suffix}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_record(query, run, context, result, model, dropped),
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"实际模型身份：{result.model_id}｜耗时：{result.elapsed_seconds:.2f}s"
          f"｜用量：{result.usage.to_dict()}")
    print(f"回答条目：{len(result.answer.case_answers)}｜跳过候选："
          f"{[item.case_id for item in result.answer.skipped_candidates]}")
    print("不足说明：", result.answer.insufficiency)
    print("运行记录已写入：", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
