"""验证 evaluate 子命令的默认输入、成功保存与失败时不留半份结果；不把读数当质量结论。"""

import json
from pathlib import Path
import sys

import pytest

from casetrace import main

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


def _drop_timestamp(report):
    report.pop("generated_at")
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

    assert _drop_timestamp(json.loads(first.read_text(encoding="utf-8"))) == _drop_timestamp(
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
