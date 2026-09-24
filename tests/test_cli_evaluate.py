"""验证 evaluate 子命令的默认输入、方法选择、成功保存与失败时不留半份结果；不把读数当质量结论。"""

import json
from pathlib import Path
import sys

import pytest

from casetrace import main
from casetrace.retrieval.base import SearchHit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QRELS_RELATIVE = "data/evaluation/dev-v2/qrels.json"


def _invoke_cli(monkeypatch, capsys, *arguments):
    """在仓库根目录调用 CLI；成功返回退出码 None，失败返回 argparse 的退出码。"""
    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr(sys, "argv", ["casetrace", *arguments])
    try:
        main()
        code = None
    except SystemExit as exit_info:
        code = exit_info.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _drop_run_metadata(report):
    """剔除不参与确定性比较的运行元数据：记录生成时间与机器相关的耗时。"""
    report.pop("generated_at")
    report.pop("timing")
    return report


def test_evaluate_default_qrels_writes_report(tmp_path, monkeypatch, capsys):
    output = tmp_path / "dev-v2-bm25.json"

    code, stdout, _ = _invoke_cli(monkeypatch, capsys, "evaluate", "--output", str(output))

    assert code is None
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["benchmark"]["qrels_path"] == QRELS_RELATIVE
    assert report["benchmark"]["qrels_version"] == "dev-qrels-v2"
    assert report["summary"]["query_count"] == 3
    assert str(output) in stdout
    assert "mrr@4" in stdout and "完整排名" in stdout


def test_evaluate_repeat_runs_agree_on_ranking_and_scores(tmp_path, monkeypatch, capsys):
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    assert _invoke_cli(
        monkeypatch, capsys, "evaluate", "--qrels", QRELS_RELATIVE, "--output", str(first),
    )[0] is None
    assert _invoke_cli(
        monkeypatch, capsys, "evaluate", "--qrels", str(PROJECT_ROOT / QRELS_RELATIVE),
        "--output", str(second),
    )[0] is None

    assert _drop_run_metadata(json.loads(first.read_text(encoding="utf-8"))) == _drop_run_metadata(
        json.loads(second.read_text(encoding="utf-8"))
    )


def test_evaluate_requires_an_output_path(monkeypatch, capsys):
    code, _, stderr = _invoke_cli(monkeypatch, capsys, "evaluate")

    assert code == 2
    assert "--output" in stderr


def test_evaluate_rejects_missing_qrels_without_writing_a_report(tmp_path, monkeypatch, capsys):
    output = tmp_path / "should-not-exist.json"

    code, _, stderr = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--qrels", str(tmp_path / "missing.json"),
        "--output", str(output),
    )

    assert code == 2
    assert "missing.json" in stderr
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_evaluate_rejects_unconfirmed_labels_without_writing_a_report(tmp_path, monkeypatch, capsys):
    qrels = json.loads((PROJECT_ROOT / QRELS_RELATIVE).read_text(encoding="utf-8"))
    qrels["review_status"] = "draft_pending_human_review"
    tampered = tmp_path / "qrels.json"
    tampered.write_text(json.dumps(qrels, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "should-not-exist.json"

    code, _, stderr = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--qrels", str(tampered), "--output", str(output),
    )

    assert code == 2
    assert "human_confirmed" in stderr
    assert not output.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["qrels.json"]


def test_evaluate_rejects_changed_source_hashes_without_writing_a_report(tmp_path, monkeypatch, capsys):
    qrels = json.loads((PROJECT_ROOT / QRELS_RELATIVE).read_text(encoding="utf-8"))
    qrels["sources"]["dataset"]["sha256"] = "0" * 64
    tampered = tmp_path / "qrels.json"
    tampered.write_text(json.dumps(qrels, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "should-not-exist.json"

    code, _, stderr = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--qrels", str(tampered), "--output", str(output),
    )

    assert code == 2
    assert "SHA-256 不一致" in stderr
    assert not output.exists()


def test_evaluate_explicit_bm25_matches_default(tmp_path, monkeypatch, capsys):
    """显式 --method bm25 与省略参数等价；终端头部显示的方法名与报告记录一致。"""
    default, explicit = tmp_path / "default.json", tmp_path / "explicit.json"

    assert _invoke_cli(monkeypatch, capsys, "evaluate", "--output", str(default))[0] is None
    code, stdout, _ = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--method", "bm25", "--output", str(explicit),
    )

    assert code is None
    report = json.loads(explicit.read_text(encoding="utf-8"))
    assert f"检索方法：{report['retrieval']['method']}" in stdout
    assert _drop_run_metadata(report) == _drop_run_metadata(
        json.loads(default.read_text(encoding="utf-8"))
    )


def test_evaluate_rejects_unknown_method_without_writing_a_report(tmp_path, monkeypatch, capsys):
    """未知方法在写出任何结果之前被拒绝，退出码与既有输入错误一致。"""
    output = tmp_path / "should-not-exist.json"

    code, _, stderr = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--method", "hybrid", "--output", str(output),
    )

    assert code == 2
    assert "未实现的检索方法" in stderr and "hybrid" in stderr
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_evaluate_accepts_embedding_with_a_stubbed_retriever(tmp_path, monkeypatch, capsys):
    """embedding 已注册：方法选择与报告元数据走通；用替身替代模型，不下载、不联网。"""
    from casetrace.evaluation import runner

    class StubRetriever:
        """替身检索器：只提供公共契约要求的行为，用来验证 CLI 与报告接线。"""

        def __init__(self, documents):
            self.case_ids = sorted(documents)

        def search(self, query, *, top_k):
            return [
                SearchHit(case_id, 1.0 / rank)
                for rank, case_id in enumerate(self.case_ids, start=1)
            ][:top_k]

        def describe(self):
            return {"method": "embedding", "model": "stub-model", "model_revision": "stub-rev"}

    monkeypatch.setitem(runner.RETRIEVER_FACTORIES, "embedding", StubRetriever)
    output = tmp_path / "embedding.json"

    code, stdout, _ = _invoke_cli(
        monkeypatch, capsys, "evaluate", "--method", "embedding", "--output", str(output),
    )

    assert code is None
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["retrieval"]["method"] == "embedding"
    assert report["retrieval"]["model"] == "stub-model"
    assert report["summary"]["query_count"] == 3
    assert "检索分数不是相关概率" in stdout
