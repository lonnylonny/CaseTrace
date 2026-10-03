"""M4-03 教学练习：喂一份伪造引用的回答，看守卫在哪一层拦下它。

用法：uv run python tmp/m4_03_practice.py            默认用 C002 / E012（伪造）
      uv run python tmp/m4_03_practice.py --honest   换成 C007 / E007（真实引用）
不联网、不需要凭据；只调用公共函数，不改语料、不写运行记录。
"""

import argparse
import json
from datetime import date
from pathlib import Path

from casetrace.answer.cli import run_answer_question
from casetrace.answer.model import OfflineChatModel

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"

FAKE_ANSWER = {
    "case_answers": [{
        "case_id": "C002",
        "relevance_reason": "看起来相关",
        "query_facts": ["焊线自焊盘脱开"],
        "case_facts": ["引脚润湿不良"],
        "historical_root_cause": "引脚表面污染/氧化。",
        "historical_evidences": [{"checkpoint_id": "E012", "result": "编造的检查结果"}],
        "sources": [{"case_id": "C002", "field": "abnormal_description"}],
    }],
    "skipped_candidates": [],
    "current_gaps": [],
    "insufficiency": None,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="M4-03 引用守卫练习")
    parser.add_argument("--honest", action="store_true", help="改用真实存在的 C007 / E007")
    args = parser.parse_args()

    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    query = next(item for item in payload["queries"] if item["query_id"] == "Q005")

    answer = dict(FAKE_ANSWER)
    if args.honest:
        answer = {
            "case_answers": [{
                "case_id": "C007",
                "relevance_reason": "同为 OQC 拉力试验、键合界面脱开",
                "query_facts": ["焊线自焊盘脱开"],
                "case_facts": ["键合金球从器件焊盘表面分离"],
                "historical_root_cause": "结案确认：Wire Bond参数不当，键合界面结合强度不足。",
                "historical_evidences": [{"checkpoint_id": "E007", "result": "见原文"}],
                "sources": [
                    {"case_id": "C007", "field": "root_cause"},
                    {"case_id": "C007", "field": "checkpoint:E007"},
                ],
            }],
            "skipped_candidates": [],
            "current_gaps": [],
            "insufficiency": None,
        }

    outcome = run_answer_question(
        query["text"], date.fromisoformat(query["known_at"]),
        dataset_path=DATASET, reference_path=REFERENCE,
        model_factory=lambda: OfflineChatModel(json.dumps(answer, ensure_ascii=False)),
    )
    print("status =", outcome.status, "| exit =", outcome.exit_code)
    print("message =", outcome.message)
    print("issues =", json.dumps(outcome.record["citations"], ensure_ascii=False))
    print("candidates =", [item["case_id"] for item in outcome.record["ranking"]])
    print("answer_text kept =", bool(outcome.record["answer_text"]))
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
