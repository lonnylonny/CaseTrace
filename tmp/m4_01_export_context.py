"""M4-01 SD3：导出真实 Q005 的证据上下文，供人工检查。

跑：uv run python tmp/m4_01_export_context.py
输出：/tmp/casetrace-m4-01-context-q005.json（OS 临时文件，不入库、不覆盖 results/）
只读脚本：不改数据、不写仓库文件。
"""

import json
from datetime import date
from pathlib import Path

from casetrace.answer.context import (
    SOURCE_FIELDS,
    build_evidence_context,
    context_to_payload,
    prepare_answer_run,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
OUTPUT = Path("/tmp/casetrace-m4-01-context-q005.json")

payload = json.loads(DATASET.read_text(encoding="utf-8"))
query = payload["queries"][4]                      # Q005：含否定条件
run = prepare_answer_run(
    query["text"], date.fromisoformat(query["known_at"]),
    dataset_path=DATASET, reference_path=REFERENCE,
)
inputs = run.inputs
context = build_evidence_context(
    inputs.query, inputs.hits, inputs.records, inputs.reference, inputs.sources,
)
document = context_to_payload(context)
OUTPUT.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

print("Query（完整原文，含否定条件）：")
print("   ", document["query"])
print()
print("排名一致性：", [case["case_id"] for case in document["cases"]]
      == [item["case_id"] for item in run.run_metadata["ranking"]])
print()
print("快照身份：")
print("    dataset SHA-256 ：", run.run_metadata["snapshot"]["dataset_sha256"])
print("    reference SHA-256：", run.run_metadata["snapshot"]["reference_sha256"])
print()
for case in document["cases"]:
    source_keys = sorted(case["source"])
    print(f"rank {case['rank']}  {case['case_id']}")
    print(f"    来源字段：{source_keys}")
    print(f"    允许字段内：{set(source_keys) <= set(SOURCE_FIELDS)}")
    print(f"    Detail {len(case['details'])} 条 / Evidence {len(case['evidences'])} 条"
          f" / 检查项 {[item['checkpoint_id'] for item in case['evidences']]}")
    print(f"    异常工序：{case['processes']}")
    print(f"    背景：{case['background']}")
print()
serialized = json.dumps(document, ensure_ascii=False)
for forbidden in ("generation_note", "review_status", "rationale", "judgment", "qrels"):
    print(f"泄漏自检 {forbidden:16s}：{'出现' if forbidden in serialized else '未出现'}")
print()
print("上下文已写入：", OUTPUT)
