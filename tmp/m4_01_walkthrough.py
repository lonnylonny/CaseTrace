"""把"组装上下文"这件事拆成 7 步，每步都打印真实结果，方便照着看。

跑：uv run python tmp/m4_01_walkthrough.py
注意：这是"算一遍给你看"，不是你的函数；循环、守卫和最后装包还是要你自己接。
"""

import json
from datetime import date
from pathlib import Path

from casetrace.answer.context import prepare_answer_run, product_backgrounds

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/dev/demo-v3.json"
REFERENCE = ROOT / "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"

payload = json.loads(DATASET.read_text(encoding="utf-8"))
dev_query = payload["queries"][4]
run = prepare_answer_run(
    dev_query["text"], date.fromisoformat(dev_query["known_at"]),
    dataset_path=DATASET, reference_path=REFERENCE,
)
hits, records, reference, sources = (
    run.inputs.hits, run.inputs.records, run.inputs.reference, run.inputs.sources,
)
print("=" * 70)


# ── 第 1 步：名单 ─────────────────────────────────────────────────────
print("第 1 步 名单（hits）：每条只有 case_id、score、matched_terms")
for hit in hits:
    print("   ", hit.case_id, round(hit.score, 3))
print("=" * 70)


# ── 第 2 步：把"档案柜"变成"按编号查"的字典 ───────────────────────────
print("第 2 步 建 case_by_id：list → 字典")
print("   改之前 records['cases'] 是：", type(records["cases"]).__name__,
      "，长度", len(records["cases"]))
case_by_id = {item.case_id: item for item in records["cases"]}
print("   改之后 case_by_id 是：", type(case_by_id).__name__)
print("   它的键：", sorted(case_by_id))
print("   所以现在可以这样判断'在不在'：", "C007" in case_by_id, "|", "C999" in case_by_id)
print("=" * 70)


# ── 第 3 步：取一条命中的正文 ─────────────────────────────────────────
print("第 3 步 取 C007 的正文（一个 Case 对象）")
case = case_by_id["C007"]
print("   case.case_id              =", case.case_id)
print("   case.abnormal_description =", case.abnormal_description[:30], "…")
print("   case.root_cause           =", case.root_cause[:30], "…")
print("=" * 70)


# ── 第 4 步：筛出这个 Case 的全部 Detail ──────────────────────────────
print("第 4 步 筛出 case_id 等于 C007 的全部 Detail")
details = [item for item in records["details"] if item.case_id == case.case_id]
print("   筛出", len(details), "条")
for item in details:
    print("   ", item.detail_id, item.product_id, item.production_lot, item.detection_stage)
print("=" * 70)


# ── 第 5 步：筛出这个 Case 的全部 Evidence ────────────────────────────
print("第 5 步 筛出 case_id 等于 C007 的全部 Evidence")
evidences = [item for item in records["evidences"] if item.case_id == case.case_id]
print("   筛出", len(evidences), "条")
for item in evidences:
    print("   ", item.checkpoint_id, item.relevance, item.result[:25], "…")
print("=" * 70)


# ── 第 6 步：来源记录，过滤掉不该给模型的字段 ─────────────────────────
print("第 6 步 来源记录：过滤前 vs 过滤后")
raw_source = sources[case.case_id]
print("   过滤前的键：", sorted(raw_source))
SOURCE_FIELDS = ("sheet", "failure_mode_id", "root_cause", "corrective_action", "closure_status")
source = {key: value for key, value in raw_source.items() if key in SOURCE_FIELDS}
print("   过滤后的键：", sorted(source))
print("（被去掉的 generation_note / review_status 就是不该给模型看的东西）")
print("=" * 70)


# ── 第 7 步：背景来自主数据 ──────────────────────────────────────────
print("第 7 步 背景：把第 4 步筛出来的 details 交给现成函数")
background = product_backgrounds(reference, details)
for item in background:
    print("   ", item)
print("=" * 70)

print("到这里，装一块 CaseEvidence 需要的 7 样东西你都有了：")
print("   rank=1, case_id='C007', case=case, details=details,")
print("   evidences=evidences, source=source, background=background")
print("把它们塞进 CaseEvidence(...)，再把 4 条塞进 EvidenceContext(query=..., cases=[...])")
print("这最后一步，还有循环和两条守卫，就是你要写的部分。")
