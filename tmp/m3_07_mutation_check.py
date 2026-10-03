"""M3-07 SD2-5 破坏验证：临时改坏 compare.py，确认新测试真的会失败，再恢复原字节。

每处变异：写坏源码 → 跑 tests/evaluation/test_compare.py → 打印 pytest 摘要 → finally 恢复。
运行前后比对源码 SHA-256，证明工作树没有被留下改动。
用法：uv run python tmp/m3_07_mutation_check.py
"""

import hashlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "src" / "casetrace" / "evaluation" / "compare.py"
TEST_FILE = "tests/evaluation/test_compare.py"

# 每处变异：说明 → （被替换的原文, 替换为）。原文必须在本文件里唯一出现。
MUTATIONS = (
    (
        "去掉 schema_version（应让旧 schema 测试失败）",
        '    "schema_version",\n',
        "",
    ),
    (
        "去掉 benchmark.qrels_version（应让跨 benchmark 测试失败）",
        '    "benchmark.qrels_version",\n',
        "",
    ),
    (
        "去掉 metrics.ks（应让指标口径测试失败）",
        '    "metrics.ks",\n',
        "",
    ),
    (
        "加入 retrieval.method（应让“不同模型允许比较”失败）",
        '    "schema_version",\n',
        '    "schema_version",\n    "retrieval.method",\n',
    ),
    (
        "缺字段消息去掉字段路径（应让缺字段测试失败）",
        'raise ValueError(f"结果报告 | {path} | {side}侧缺少该字段")',
        'raise ValueError("缺少字段")',
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tests() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", TEST_FILE],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    if not lines:
        return "(pytest 无输出)"
    failed = [line.split(" - ")[0] for line in lines if line.startswith(("FAILED", "ERROR"))]
    detail = "、".join(failed) if failed else "（无失败明细）"
    return f"{lines[-1]}；失败用例：{detail}"


def main() -> None:
    original = SOURCE.read_text(encoding="utf-8")
    before = sha256(SOURCE)
    print(f"改动前源码 SHA-256：{before}")
    try:
        for description, old, new in MUTATIONS:
            count = original.count(old)
            if count != 1:
                print(f"{description}：变异目标出现 {count} 次，跳过")
                continue
            SOURCE.write_text(original.replace(old, new), encoding="utf-8")
            print(f"{description}\n    → {run_tests()}")
    finally:
        SOURCE.write_text(original, encoding="utf-8")
    after = sha256(SOURCE)
    print(f"恢复后源码 SHA-256：{after}")
    print("源码已恢复为原字节" if after == before else "警告：源码与改动前不一致！")


if __name__ == "__main__":
    main()
