"""M4-03 引用守卫：核对回答里的引用能否在本次上下文中定位。

守卫只做结构核对，共四项：

1. 引用的 Case 属于本次上下文（本次 R3 的候选），不是其它 Case；
2. 每条来源字段确实挂在该条回答自己的 Case 上，不跨 Case 挂靠；
3. Detail / 检查用实体 ID 能在该 Case 的上下文子记录里找到；
4. 字段名是本次上下文中可定位的 Case 字段、列表字段（`background` / `processes`）
   或来源记录字段，且有内容。

明确不做的事：判断引用是否**支持**它所在的那句话。引用能定位只说明它存在且可复查，
“引用存在”不等于“引用支持句子”，语义支持必须另行人工审阅（M4-04）。
守卫不改写回答、不自动修复、不重试；有问题就明确失败，由调用方决定后续处理。
"""

from dataclasses import dataclass, fields

from casetrace.answer.context import EvidenceContext
from casetrace.answer.generation import GroundedAnswer, SourceRef
from casetrace.data.dataset_model import Case

# 来源字段写法：Case 字段直接写字段名；Detail 与检查结果写带前缀的实体 ID。
DETAIL_PREFIX = "detail:"
CHECKPOINT_PREFIX = "checkpoint:"
CASE_FIELDS = tuple(item.name for item in fields(Case))
# 随上下文一起提供的列表字段：主数据背景与已确认异常工序；模型引用它们也要能定位。
LIST_FIELDS = ("background", "processes")
# 显式容器路径只在该容器内查找；扁平兼容写法在后面的分支单独处理。
CONTAINER_PREFIXES = ("case.", "source.")

# 问题分类：稳定字符串便于测试与运行记录引用，不用自然语言做断言。
UNKNOWN_CASE = "unknown_case"        # 引用的 Case 不在本次上下文中
CROSS_CASE = "cross_case"            # 来源挂到了别的 Case 上
MISSING_TARGET = "missing_target"    # 本 Case 的上下文里没有这个 Detail / 检查
UNKNOWN_FIELD = "unknown_field"      # 字段名不可定位，或该字段没有内容
INVALID_FIELD = "invalid_field"      # 字段写法不合法（如前缀后为空）
DUPLICATE_CASE = "duplicate_case"    # 同一 Case 重复出现
CONFLICTING_CASE = "conflicting_case"  # 同一 Case 既给出相关理由又列为跳过候选
MISSING_SOURCE = "missing_source"    # 历史改善措施未附其对应字段的来源


@dataclass(frozen=True)
class CitationIssue:
    """一条引用问题：位置（可回到回答的哪一项）、分类与可读说明。"""

    location: str
    kind: str
    detail: str

    def to_payload(self) -> dict:
        return {"location": self.location, "kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class CitationReport:
    """一次引用校验的结论：检查了多少条引用、发现了哪些问题。

    `checked` 统计被核对的引用条目数（Case 归属、来源字段、历史检查、跳过候选），
    不是语义支持数：即使 `issues` 为空，也只说明引用可以定位。
    """

    checked: int
    issues: tuple[CitationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    def to_payload(self) -> dict:
        return {
            "checked": self.checked,
            "issue_count": len(self.issues),
            "issues": [item.to_payload() for item in self.issues],
        }


class CitationError(ValueError):
    """回答里存在无法定位、跨 Case 或不存在的引用；本次回答按失败处理。"""

    def __init__(self, report: CitationReport) -> None:
        self.report = report
        summary = "；".join(f"{item.location} {item.detail}" for item in report.issues[:5])
        if len(report.issues) > 5:
            summary += f"；…（共 {len(report.issues)} 项）"
        super().__init__(f"引用校验失败：{summary}")


def _case_index(context: EvidenceContext) -> dict:
    """按 case_id 建立本次上下文的可定位索引：Case 字段值、Detail ID、检查 ID、来源字段。"""

    index = {}
    for case in context.cases:
        index[case.case_id] = {
            "case": case.case,
            "details": {item.detail_id for item in case.details},
            "checkpoints": {item.checkpoint_id for item in case.evidences},
            "source": case.source,
            "background": case.background,
            "processes": case.processes,
        }
    return index


def _candidate_ids(index: dict) -> str:
    return "、".join(sorted(index)) or "（本次没有候选）"


def _has_content(value) -> bool:
    """字段在本次上下文里是否有可引用的内容；None 与空白字符串都算没有。"""

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _field_issue(entry: dict, case_id: str, field: str, location: str) -> CitationIssue | None:
    """核对一个来源字段能否在本 Case 的上下文里定位；可定位时返回 None。"""

    for prefix in CONTAINER_PREFIXES:
        if field.startswith(prefix):
            name = field[len(prefix):]
            if not name:
                return CitationIssue(location, INVALID_FIELD, f"容器路径缺少字段名：{field!r}")
            value = None
            if prefix == "case." and name in CASE_FIELDS:
                value = getattr(entry["case"], name)
            elif prefix == "source.":
                value = entry["source"].get(name)
            if _has_content(value):
                return None
            return CitationIssue(
                location, UNKNOWN_FIELD,
                f"Case {case_id} 的容器路径 {field!r} 不存在或没有内容",
            )
    if field.startswith(DETAIL_PREFIX):
        target = field[len(DETAIL_PREFIX):]
        if not target:
            return CitationIssue(location, INVALID_FIELD, f"Detail 引用缺少 detail_id：{field!r}")
        if target not in entry["details"]:
            return CitationIssue(
                location, MISSING_TARGET,
                f"Case {case_id} 的本次上下文没有 Detail {target}",
            )
        return None
    if field.startswith(CHECKPOINT_PREFIX):
        target = field[len(CHECKPOINT_PREFIX):]
        if not target:
            return CitationIssue(location, INVALID_FIELD, f"检查引用缺少 checkpoint_id：{field!r}")
        if target not in entry["checkpoints"]:
            return CitationIssue(
                location, MISSING_TARGET,
                f"Case {case_id} 的本次上下文没有检查 {target}",
            )
        return None
    if field in CASE_FIELDS:
        if _has_content(getattr(entry["case"], field)):
            return None
        return CitationIssue(
            location, UNKNOWN_FIELD, f"Case {case_id} 的字段 {field} 在本次上下文中没有内容"
        )
    # 主数据背景与异常工序随每条 Case 一起进入上下文，是模型可见的证据，必须能定位。
    if field in LIST_FIELDS:
        if entry[field]:
            return None
        return CitationIssue(
            location, UNKNOWN_FIELD, f"Case {case_id} 的 {field} 在本次上下文中没有内容"
        )
    if field in entry["source"] and _has_content(entry["source"][field]):
        return None
    return CitationIssue(
        location, UNKNOWN_FIELD,
        f"Case {case_id} 的本次上下文没有可定位字段 {field!r}"
        f"（Case 字段：{'、'.join(CASE_FIELDS)}；另有 {'、'.join(LIST_FIELDS)}；"
        f"来源字段可写字段名或 source.<字段名>；"
        f"Detail 写 detail:<detail_id>；检查写 checkpoint:<checkpoint_id>）",
    )


def _source_issues(entry: dict | None, answer_case_id: str, source: SourceRef,
                   location: str) -> list[CitationIssue]:
    """核对一条来源引用：归属的 Case 与字段是否都能在本次上下文里定位。"""

    if source.case_id != answer_case_id:
        return [CitationIssue(
            location, CROSS_CASE,
            f"来源 {source.case_id}:{source.field} 不属于本条回答的 Case {answer_case_id}",
        )]
    if entry is None:
        # 回答的 Case 本身未知，已在 case_id 处报告，避免同一原因重复计数。
        return []
    issue = _field_issue(entry, answer_case_id, source.field, location)
    return [] if issue is None else [issue]


def _note_duplicate(seen: dict[str, str], case_id: str, location: str,
                    issues: list[CitationIssue]) -> None:
    """同一 Case 重复出现时记一条问题；位置记录便于回到回答原文。"""

    if case_id in seen:
        issues.append(CitationIssue(
            location, DUPLICATE_CASE,
            f"Case {case_id} 已在 {seen[case_id]} 出现，同一 Case 不应重复",
        ))
    else:
        seen[case_id] = location


def validate_answer_citations(
    answer: GroundedAnswer, context: EvidenceContext, *, require_relevance_source: bool = False,
) -> CitationReport:
    """逐条核对回答引用的 Case、实体 ID 与字段；只报告问题，不修改回答。

    空上下文（`context.cases == []`）时没有任何可引用的历史材料：
    回答里只要还有内容，就会因为 Case 不在上下文中而失败。
    """

    index = _case_index(context)
    issues: list[CitationIssue] = []
    checked = 0
    answered: dict[str, str] = {}
    skipped: dict[str, str] = {}

    for position, case_answer in enumerate(answer.case_answers):
        location = f"case_answers[{position}]"
        checked += 1
        entry = index.get(case_answer.case_id)
        if entry is None:
            issues.append(CitationIssue(
                f"{location}.case_id", UNKNOWN_CASE,
                f"Case {case_answer.case_id} 不在本次上下文中"
                f"（本次候选：{_candidate_ids(index)}）",
            ))
        _note_duplicate(answered, case_answer.case_id, f"{location}.case_id", issues)

        if require_relevance_source and entry is not None and not any(
            source.case_id == case_answer.case_id
            and (source.field in ("abnormal_description", "case.abnormal_description", "background")
                 or source.field.startswith(DETAIL_PREFIX))
            for source in case_answer.sources
        ):
            issues.append(CitationIssue(
                f"{location}.relevance_reason", MISSING_SOURCE,
                "相关理由必须带该 Case 的异常描述、Detail 或背景来源；仅有原因/检查来源不足",
            ))

        if case_answer.historical_corrective_action is not None and not any(
            source.case_id == case_answer.case_id
            and source.field in ("corrective_action", "case.corrective_action")
            for source in case_answer.sources
        ):
            issues.append(CitationIssue(
                f"{location}.historical_corrective_action", MISSING_SOURCE,
                "历史改善措施必须带该 Case 的 corrective_action 来源",
            ))

        for evidence_position, evidence in enumerate(case_answer.historical_evidences):
            checked += 1
            if entry is None:
                # Case 本身已报未知，不再为它派生的检查重复报同一问题。
                continue
            if evidence.checkpoint_id not in entry["checkpoints"]:
                issues.append(CitationIssue(
                    f"{location}.historical_evidences[{evidence_position}].checkpoint_id",
                    MISSING_TARGET,
                    f"Case {case_answer.case_id} 的本次上下文没有检查 {evidence.checkpoint_id}",
                ))

        for source_position, source in enumerate(case_answer.sources):
            checked += 1
            issues.extend(_source_issues(
                entry, case_answer.case_id, source, f"{location}.sources[{source_position}]",
            ))

    for position, candidate in enumerate(answer.skipped_candidates):
        location = f"skipped_candidates[{position}].case_id"
        checked += 1
        if candidate.case_id not in index:
            issues.append(CitationIssue(
                location, UNKNOWN_CASE,
                f"Case {candidate.case_id} 不在本次上下文中"
                f"（本次候选：{_candidate_ids(index)}）",
            ))
        _note_duplicate(skipped, candidate.case_id, location, issues)
        if candidate.case_id in answered:
            issues.append(CitationIssue(
                location, CONFLICTING_CASE,
                f"Case {candidate.case_id} 既在 {answered[candidate.case_id]} 给出相关理由，"
                "又列为跳过候选",
            ))

    return CitationReport(checked=checked, issues=tuple(issues))


def ensure_answer_citations(
    answer: GroundedAnswer, context: EvidenceContext, *, require_relevance_source: bool = False,
) -> CitationReport:
    """校验引用；有问题抛 `CitationError`，通过时返回报告供运行记录使用。"""

    report = validate_answer_citations(answer, context,
                                       require_relevance_source=require_relevance_source)
    if not report.ok:
        raise CitationError(report)
    return report
