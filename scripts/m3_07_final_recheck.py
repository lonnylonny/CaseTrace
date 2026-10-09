"""M3-07 SD4 复跑核对（只读）：最终结果 vs M3-06 R3 vs 复跑结果。

用途是复算选型报告第 7.3–7.4 节的全部结论：

1. `results/dev-v3-m3-07-final.json`（最终正式结果）与 `results/dev-v3-m3-06-r3.json`
   的六个可比面板是否一致、逐 Query 差值是否为 0；
2. 同命令复跑的第二份结果与最终结果的差异是否只落在
   `generated_at` / `timing` 数值 / `reproducibility.git_status_paths`。

复跑文件默认取 /tmp/casetrace-dev-v3-m3-07-final-recheck.json（也可用命令行第 1 个参数指定）；文件不存在时明确提示，
不假装已经核对。本脚本不跑检索、不写文件。
运行：uv run python scripts/m3_07_final_recheck.py
"""

import hashlib
import json
import sys
from pathlib import Path

from casetrace.evaluation.compare import (
    check_comparable,
    load_per_query_scores,
    per_query_deltas,
)

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "results" / "dev-v3-m3-07-final.json"
R3 = ROOT / "results" / "dev-v3-m3-06-r3.json"
RECHECK = Path("/tmp/casetrace-dev-v3-m3-07-final-recheck.json")

# 同 benchmark 必须一致的面板；其余顶层键允许随运行变化。
SAME_PANELS = ("schema_version", "benchmark", "retrieval", "metrics", "queries", "summary")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_panels(left: dict, right: dict, left_label: str, right_label: str) -> list[str]:
    differing = [key for key in SAME_PANELS if left[key] != right[key]]
    state = "全部一致" if not differing else f"不一致：{differing}"
    print(f"- 可比面板 {left_label} vs {right_label}：{state}")
    return differing


def main() -> None:
    final, r3 = load(FINAL), load(R3)
    recheck_path = Path(sys.argv[1]) if len(sys.argv) > 1 else RECHECK
    print("# M3-07 SD4 复跑核对（只读）\n")
    print(f"- 最终结果 {FINAL.relative_to(ROOT)} SHA-256：`{sha256(FINAL)}`")
    print(f"- M3-06 R3 {R3.relative_to(ROOT)} SHA-256：`{sha256(R3)}`\n")

    print("## 1 最终结果 vs M3-06 R3\n")
    compare_panels(final, r3, "final", "r3")
    print(f"- check_comparable：{check_comparable(final, r3)}")
    deltas = per_query_deltas(load_per_query_scores(r3), load_per_query_scores(final))
    print(f"- 逐 Query recall@4 差值：{ {q: m['recall@4'] for q, m in deltas.items()} }")
    print(f"- 顶层键差异：{[key for key in final if final[key] != r3.get(key)]}\n")

    print("## 2 最终结果 vs 同命令复跑\n")
    if not recheck_path.is_file():
        print(f"- 复跑文件不存在：{recheck_path}")
        print("- 生成命令：uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json "
              f"--method bm25_drop_negation_labels --output {recheck_path}")
        return
    recheck = load(recheck_path)
    print(f"- 复跑结果 SHA-256：`{sha256(recheck_path)}`")
    compare_panels(final, recheck, "final", "recheck")
    print(f"- 顶层键差异：{[key for key in final if final[key] != recheck.get(key)]}")
    print("- timing 差异字段："
          f"{[key for key in final['timing'] if final['timing'][key] != recheck['timing'].get(key)]}")
    print("- reproducibility 差异字段："
          f"{[key for key in final['reproducibility'] if final['reproducibility'][key] != recheck['reproducibility'].get(key)]}")


if __name__ == "__main__":
    main()
