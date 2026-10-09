"""M3-07 SD2 复核：用 check_comparable 核对汇总要用的结果报告是否属于同一 benchmark。

只读 results/ 下的已验收产物，不写文件、不改产物；所有判定都打印出来供人工核对。
用法：uv run python scripts/m3_07_comparable_check.py
"""

import itertools
import json
from pathlib import Path

from casetrace.evaluation.compare import check_comparable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# M3-07 汇总要放进同一张质量对比表的同版产物：四类方法 + M3-06 变体。
DEV_V3_ARTIFACTS = (
    "dev-v3-bm25-m3-04-fixed.json",
    "dev-v3-embedding-m3-04-fixed.json",
    "dev-v3-hybrid-m3-04-fixed.json",
    "dev-v3-rerank-m3-05.json",
    "dev-v3-m3-06-r0.json",
    "dev-v3-m3-06-r1.json",
    "dev-v3-m3-06-r2.json",
    "dev-v3-m3-06-r3.json",
)
# 历史版本结果：与 dev-v3 不同 benchmark，用来确认拒绝路径真的会触发。
OLD_ARTIFACTS = ("dev-v2-bm25-m3-01.json", "dev-v2-bm25.json")


def load(name: str) -> dict:
    return json.loads((PROJECT_ROOT / "results" / name).read_text(encoding="utf-8"))


def main() -> None:
    reports = {name: load(name) for name in DEV_V3_ARTIFACTS}
    pairs = list(itertools.combinations(DEV_V3_ARTIFACTS, 2))
    rejected = []
    for left, right in pairs:
        try:
            check_comparable(reports[left], reports[right])
        except ValueError as exc:
            rejected.append((left, right, str(exc)))
    print(f"dev-v3 同版产物两两核对：{len(pairs)} 对，判定不可比 {len(rejected)} 对")
    for left, right, message in rejected:
        print(f"  不可比 {left} × {right}：{message}")

    for name in OLD_ARTIFACTS:
        try:
            check_comparable(reports[DEV_V3_ARTIFACTS[0]], load(name))
        except ValueError as exc:
            print(f"跨版本 {name}：已拒绝 | {exc}")
        else:
            print(f"跨版本 {name}：未拒绝（不符合预期）")


if __name__ == "__main__":
    main()
