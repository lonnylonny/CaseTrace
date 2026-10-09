"""真实调用脚本的离线测试：防覆盖检查必须发生在任何模型调用之前。"""

import importlib.util
from pathlib import Path
import sys

import pytest

from casetrace.answer.cli import AnswerOutcome

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/m4_04_run_all.py"
spec = importlib.util.spec_from_file_location("m4_batch", SCRIPT)
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


@pytest.mark.parametrize("suffix", ["json", "cli.txt"])
def test_existing_target_stops_whole_batch_before_model(monkeypatch, tmp_path, suffix):
    old = tmp_path / f"q002.{suffix}"
    old.write_bytes(b"historical evidence")
    calls = []
    monkeypatch.setattr(batch, "run_answer_question", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--output-dir", str(tmp_path)])

    assert batch.main() == 2
    assert calls == []
    assert old.read_bytes() == b"historical evidence"
    assert not (tmp_path / "q001.json").exists()


def test_failed_answer_is_preserved_and_returns_nonzero(monkeypatch, tmp_path):
    outcome = AnswerOutcome("format_failed", {"status": "format_failed",
                           "response": {"elapsed_seconds": 1,
                           "usage": {}}, "citations": {"checked": 0, "issue_count": 0}},
                           "bad format")
    monkeypatch.setattr(batch, "run_answer_question", lambda *a, **k: outcome)
    monkeypatch.setattr(batch, "format_answer_text", lambda result: "failure evidence")
    monkeypatch.setattr(batch, "report_hits", lambda ids: None)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--query-id", "Q001",
                                     "--output-dir", str(tmp_path)])

    assert batch.main() != 0
    assert '"format_failed"' in (tmp_path / "q001.json").read_text()
    assert (tmp_path / "q001.cli.txt").read_text() == "failure evidence"
    assert batch.main() == 2  # 失败证据也不能覆盖
