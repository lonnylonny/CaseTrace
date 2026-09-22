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
    demo.add_argument("--top-k", type=int, default=4)
    demo.add_argument("--data", type=Path, default=Path("data/dev/demo.json"))
    demo.add_argument("--reference", type=Path, default=Path(
        "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"))
    demo.add_argument("--json", action="store_true", help="输出可供程序读取的 JSON")
    evaluate = commands.add_parser("evaluate", help="在已确认的 benchmark 上评估 BM25 检索")
    evaluate.add_argument("--qrels", type=Path, default=Path("data/evaluation/dev-v2/qrels.json"),
                          help="已确认的 qrels 文件；默认使用活动 dev-v2 版本")
    evaluate.add_argument("--output", type=Path, required=True,
                          help="结果 JSON 的保存路径；先写临时文件再原子替换")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    if args.command == "evaluate":
        from casetrace.evaluation.runner import run_evaluation, write_report

        try:
            report = run_evaluation(args.qrels)
            output = write_report(report, args.output)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
        benchmark = report["benchmark"]
        print(f"评估输入：{benchmark['qrels_path']}（{benchmark['qrels_version']} / "
              f"{benchmark['split']} / 确认日 {benchmark['confirmed_on']}）")
        print(f"语料 {report['retrieval']['corpus_size']} 条；结果已写入 {output}\n")
        for query in report["queries"]:
            ranking = " > ".join(item["case_id"] for item in query["ranked"]) or "（无返回）"
            positives = "、".join(query["relevant_case_ids"]) or "无正例"
            print(f"{query['query_id']}  正例：{positives}")
            print(f"  完整排名：{ranking}")
        print()
        for key, metric in report["summary"]["metrics"].items():
            value = "不适用" if metric["value"] is None else f"{metric['value']:.4f}"
            line = f"{key:12s} {value}  参与 {len(metric['included_query_ids'])} 条"
            if metric["excluded"]:
                excluded = "、".join(
                    f"{item['query_id']}（{item['reason']}）" for item in metric["excluded"])
                line += f"；排除 {excluded}"
            print(line)
        if report["summary"]["no_relevant_query_ids"]:
            print(f"无正例 Query：{'、'.join(report['summary']['no_relevant_query_ids'])}")
        state = "脏工作区" if report["reproducibility"]["git_dirty"] else "干净"
        print(f"\n结果 schema：{report['schema_version']}；git 状态：{state}；"
              "BM25 分数不是相关概率，读数不代表已确认的质量结论。")
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
        processes = [f"{name} ({key})" for key, name in zip(
            hit["abnormal_processes"], hit["abnormal_process_names"],
        )]
        print(f"   异常站点：{', '.join(processes)}")
        print(f"   匹配词：{', '.join(hit['matched_terms'])}")
        print(f"   历史结案原因：{hit['root_cause']}")
        for evidence in hit["evidences"]:
            print(f"   来源 {evidence['checkpoint_id']}：{evidence['result']}")
        print()
