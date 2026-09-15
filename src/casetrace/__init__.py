"""CaseTrace：辅助技术异常调查的历史案例检索系统。"""


def main() -> None:
    """命令行入口；检索逻辑保留在模块内，后续 API 可直接复用。"""
    import argparse
    import json
    from pathlib import Path

    from casetrace.demo import run_demo

    parser = argparse.ArgumentParser(description="CaseTrace 历史案例检索")
    commands = parser.add_subparsers(dest="command")
    demo = commands.add_parser("demo", help="在开发样例上运行 BM25 检索")
    demo.add_argument("--query", help="当前已知的异常描述；省略时使用默认示例")
    demo.add_argument("--top-k", type=int, default=3)
    demo.add_argument("--data", type=Path, default=Path("data/dev/demo.json"))
    demo.add_argument("--reference", type=Path, default=Path(
        "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"))
    demo.add_argument("--json", action="store_true", help="输出可供程序读取的 JSON")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    try:
        result = run_demo(args.data, args.reference, query=args.query, top_k=args.top_k)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"开发样例：{result['case_count']} 条，待人工审阅；BM25 分数不是相关概率。")
    print(f"当前查询：{result['query']}\n")
    if not result["results"]:
        print("没有词项匹配的历史案例。可以补充已知的异常表现或技术术语。")
    for rank, hit in enumerate(result["results"], start=1):
        print(f"{rank}. {hit['case_id']}  BM25={hit['score']:.3f}")
        print(f"   历史异常：{hit['abnormal_description']}")
        print(f"   匹配词：{', '.join(hit['matched_terms'])}")
        print(f"   历史结案原因：{hit['root_cause']}")
        for evidence in hit["evidences"]:
            print(f"   来源 {evidence['checkpoint_id']}：{evidence['result']}")
        print()
