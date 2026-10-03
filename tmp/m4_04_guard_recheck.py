"""M4-04 临时核对：用 Q002 的失败回答在修复后的守卫下重新校验（不调用模型）。

守卫修复（LIST_FIELDS = background / processes）后，之前被判 unknown_field 的
真实回答应当通过；本脚本只读，用来确认修复确实解决了那一条失败，不产生新产物。
"""

import json
from datetime import date
from pathlib import Path
import sys

from casetrace.answer.context import build_evidence_context, prepare_answer_run
from casetrace.answer.generation import parse_grounded_answer
from casetrace.answer.validation import validate_answer_citations

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = ROOT / "results/m4/dev-v3-answer-v1/q002.citation-failed.json"
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RECORD
    record = json.loads(path.read_text(encoding="utf-8"))
    query = record["query"]
    run = prepare_answer_run(
        query["text"], date.fromisoformat(query["known_at"]),
        dataset_path=DATASET, reference_path=REFERENCE,
    )
    inputs = run.inputs
    context = build_evidence_context(
        inputs.query, inputs.hits, inputs.records, inputs.reference, inputs.sources,
    )
    answer = parse_grounded_answer(record["answer_text"])
    report = validate_answer_citations(answer, context)
    print("ok:", report.ok, "checked:", report.checked, "issue_count:", len(report.issues))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
