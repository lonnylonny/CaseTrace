"""The M3 summary must stop before quality comparisons when benchmarks differ."""

import copy
import runpy
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "tmp" / "m3_07_selection_tables.py"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("benchmark.dataset.sha256", "different-corpus"),
        ("metrics.ks", [1, 3]),
    ],
)
def test_incomparable_result_stops_quality_tables(monkeypatch, capsys, field, replacement):
    main = runpy.run_path(str(SCRIPT))["main"]
    original_load = main.__globals__["load"]

    def load_with_incompatible_embedding(path):
        report = original_load(path)
        if "embedding-m3-04-fixed" in path:
            report = copy.deepcopy(report)
            target = report
            parts = field.split(".")
            for part in parts[:-1]:
                target = target[part]
            target[parts[-1]] = replacement
        return report

    monkeypatch.setitem(main.__globals__, "load", load_with_incompatible_embedding)

    with pytest.raises(ValueError, match=field):
        main()

    output = capsys.readouterr().out
    assert "## 2 汇总指标" not in output
    assert "## 3 逐 Query 差值" not in output
