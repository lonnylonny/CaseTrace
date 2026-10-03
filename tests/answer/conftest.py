"""M4-01 测试夹具：最小自造语料 + 可对照快照，不依赖 dev-v3 的文件哈希。

自造语料只用于检查边界行为；真实 dev-v3 路径另有单独测试。
夹具里故意放了不属于来源允许字段的内容，用来检查"标签/生成元数据不进入上下文"。
共享数据一律通过夹具传递，符合本仓库测试目录不使用包的既有约定。
"""

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from casetrace.answer.context import CorpusSnapshot

SNAPSHOT_KNOWN_AT = date(2026, 9, 15)

# 只用于边界检查：这些字符串一旦出现在模型上下文里，说明来源过滤被破坏。
POISON_GENERATION_NOTE = "POISON-GENERATION-NOTE"
POISON_RATIONALE = "POISON-RATIONALE"
POISON_REVIEW_STATUS = "POISON-REVIEW-STATUS"

# 自造语料的 Query：含标识标签词、生产批 ID 与一条否定小句，用于区分
# "R3 计分时删词" 与 "生成输入保留原文" 这两件事。
SELF_MADE_QUERY = "涉及产品 P1，客户 CUS1，生产批 DEV_PL_1，焊线脱落，已排除运输碰伤的可能"


@pytest.fixture
def answer_query():
    return SELF_MADE_QUERY


@pytest.fixture
def answer_poison():
    """来源记录里不属于允许字段的内容；出现即说明边界被破坏。"""

    return {
        "generation_note": POISON_GENERATION_NOTE,
        "rationale": POISON_RATIONALE,
        "review_status": POISON_REVIEW_STATUS,
    }


@pytest.fixture
def make_snapshot(reference_path):
    """构造测试快照；默认取语料与主数据文件的真实哈希。"""

    def _make(path: Path, *, known_at: date = SNAPSHOT_KNOWN_AT,
              dataset_sha256: str | None = None,
              reference_sha256: str | None = None) -> CorpusSnapshot:
        return CorpusSnapshot(
            snapshot_id="test-snapshot",
            known_at=known_at,
            dataset_sha256=dataset_sha256 or hashlib.sha256(path.read_bytes()).hexdigest(),
            reference_sha256=(reference_sha256
                              or hashlib.sha256(reference_path.read_bytes()).hexdigest()),
            basis="测试用快照：语料在该时点前已结案且完整可用。",
        )

    return _make


@pytest.fixture
def answer_snapshot(answer_dataset, make_snapshot):
    return make_snapshot(answer_dataset[0])


@pytest.fixture
def answer_dataset(tmp_path):
    """三条最小 Case（同产品、同 Failure Mode）；返回 (JSON 路径, payload)。"""

    spec = (
        ("C1", "焊线脱落，表面污染", "表面污染", "改善清洁", "P004"),
        ("C2", "焊线脱落，参数异常", "参数异常", "优化参数", "P004"),
        ("C3", "模压空洞", "表面污染", "改善清洁", "P007"),
    )
    payload = dict(cases=[], details=[], evidences=[], groups=[], memberships=[], sources={},
                   split="development", review_status="draft_pending_human_review",
                   queries=[{"query_id": "Q-TEST", "text": SELF_MADE_QUERY,
                             "known_at": SNAPSHOT_KNOWN_AT.isoformat()}])
    for index, (case_id, description, root_cause, action, process_id) in enumerate(spec, start=1):
        payload["cases"].append(dict(
            case_id=case_id, abnormal_description=description, root_cause=root_cause,
            corrective_action=action, investigation_others=None,
            abnormal_processes=[process_id],
        ))
        payload["details"].append(dict(
            detail_id=f"D{index}", case_id=case_id, product_id="P1", customer_lot="CL1",
            production_lot="PL1", production_time=date(2026, 6, 1).isoformat(),
            detection_stage="OQC", detection_time=date(2026, 6, index).isoformat(),
            abnormal_types=["00001"], affected_qty=100, disposition="报废",
        ))
        payload["evidences"].append(dict(
            checkpoint_id=f"E{index}", case_id=case_id, checkpoint_type="QC", custom_name=None,
            result="观察到表面污染", relevance="related",
        ))
        payload["sources"][case_id] = dict(
            sheet="failure_modes", failure_mode_id="00001", root_cause=root_cause,
            corrective_action=action, closure_status="confirmed",
            generation_note=POISON_GENERATION_NOTE, rationale=POISON_RATIONALE,
            review_status=POISON_REVIEW_STATUS,
        )
    path = tmp_path / "answer-demo.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, payload


@pytest.fixture(autouse=True)
def _no_real_env_file(monkeypatch):
    """answer 测试不读本机真实 .env：把加载器替换为无害空实现。

    真实 .env 的行为在 tests/test_env.py 用 tmp_path 显式隔离测试；
    这里只保证 answer 各测试不因用户本机存在 .env 而意外读到真实凭据。
    """
    monkeypatch.setattr(
        "casetrace.answer.model.load_local_env", lambda **kwargs: set()
    )
