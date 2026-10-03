"""M4-02 版本化提示词：模板身份、渲染结果与 JSON Output 前提。"""

import pytest

from casetrace.answer.prompt import (
    EVIDENCE_RULES,
    PROMPTS_DIR,
    PROMPT_VERSION,
    RULE_PLACEHOLDER,
    load_prompt_template,
    prompt_path,
    render_system_prompt,
)

# 只用于检查渲染行为；真正的证据约束由用户核心实践 B 写入 EVIDENCE_RULES。
USER_RULES = (
    "历史记录只能表述为历史：不写成当前 Incident 的结论、建议或已完成的检查。",
    "只能使用给定证据中的 case_id、字段与原文，不补充外部知识。",
)

# 输出契约里必须出现的字段名；模型缺少它们时结构化回答无法解析。
CONTRACT_FIELDS = (
    "case_answers", "case_id", "relevance_reason", "query_facts", "case_facts",
    "historical_root_cause", "historical_corrective_action", "historical_evidences", "sources",
    "skipped_candidates", "current_gaps", "insufficiency",
)


def test_prompt_is_a_versioned_file():
    path = prompt_path()
    assert path.parent == PROMPTS_DIR
    assert path.name == f"{PROMPT_VERSION}.md"
    assert path.is_file()
    assert RULE_PLACEHOLDER in load_prompt_template()


def test_render_includes_rules_and_output_contract():
    prompt = render_system_prompt(evidence_rules=USER_RULES)

    assert RULE_PLACEHOLDER not in prompt
    for rule in USER_RULES:
        assert f"- {rule}" in prompt
    for field in CONTRACT_FIELDS:
        assert field in prompt
    # JSON Output 要求 prompt 中出现 json 字样，否则调用会失败。
    assert "JSON" in prompt


def test_render_marks_rules_that_are_not_written_yet():
    prompt = render_system_prompt(evidence_rules=())

    assert RULE_PLACEHOLDER not in prompt
    assert "尚未写入证据约束" in prompt


def test_default_rules_treat_source_text_instructions_as_data():
    """默认证据约束必须禁止执行历史原文里的指令，否则原文可以反过来指挥模型。"""

    rules = "\n".join(EVIDENCE_RULES)

    assert "指令" in rules and "不得执行" in rules
    assert "不得执行" in render_system_prompt()


def test_render_rejects_blank_rule():
    with pytest.raises(ValueError, match="空字符串"):
        render_system_prompt(evidence_rules=["  "])


def test_unknown_prompt_version_fails():
    with pytest.raises(FileNotFoundError, match="提示词模板不存在"):
        load_prompt_template("grounded_answer_v99")
