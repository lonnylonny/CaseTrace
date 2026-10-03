# M4 → M5：核心复用与存储接缝

状态：M4 accepted；2026-10-03 Pre-M5 审计通过。本页供 M5 实施时查接口，当前范围和必须保持的行为以 [Current Plan §§3、4、7](../current-plan.md)为准。本轮未开始 PostgreSQL / FastAPI。

## 1. 现有可复用入口

| 入口 | 模块 | 职责与边界 |
|---|---|---|
| `run_answer_question(query, known_at, *, dataset_path, reference_path, model_factory, ...)` | `answer.cli` | 完整编排，返回 `AnswerOutcome`；不解析 argparse、不 print、不写输出文件，API 可直接调用 |
| `prepare_answer_run(...)` | `answer.context` | 加载/验证、快照检查、一次 R3 检索，返回原始排名及元数据；不读 qrels |
| `build_retriever_from_records(records, reference, *, method=...)` | `evaluation.runner` | 从已加载记录建索引；不要求 benchmark / qrels，可直接复用 |
| `build_evidence_context(query, hits, records, reference, sources)` | `answer.context` | 按命中顺序组织白名单原文与来源，保留原始 Query |
| `generate_grounded_answer(query, context, model, *, on_messages=None)` | `answer.generation` | 消息组装、一次模型调用及结构解析；空上下文不调用 |
| `ensure_answer_citations(answer, context, *, require_relevance_source=True)` | `answer.validation` | 核对 Case/字段/Detail/checkpoint 归属和存在，不证明语义支持 |
| `format_answer_text(outcome)` | `answer.cli` | 纯文本渲染，内容与运行记录同源 |

`answer.cli` 的文件名不表示整个模块只能用于终端。CLI 适配层是 `run_answer_command` / `resolve_query`；M5 API 调用应用函数并映射返回状态，不经 subprocess 调 CLI。同步调用与逐请求建小索引满足当前九案展示范围，暂不为生产并发、连接池或缓存设计提前拆层。

```python
from datetime import date
from pathlib import Path
from casetrace.answer.cli import build_model, run_answer_question

outcome = run_answer_question(
    query, date(2026, 9, 15),
    dataset_path=Path("data/dev/demo-v3.json"),
    reference_path=Path("data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"),
    model_factory=lambda: build_model("deepseek-flash"),
)
# outcome.status / outcome.record / outcome.message；exit_code 是 CLI 映射属性。
```

`ok` 与 `no_hits` 是正常结果；`model_failed`、`format_failed`、`citation_failed` 是不同失败。输入、语料或快照前提错误由异常报告；当前 CLI 将 `ValueError` / `OSError` 映射为输入失败。API 的 HTTP 映射留在 M5，不复制这些核心判断。

## 2. M5 需要调整的文件加载接缝

**当前仍绑定文件，不能只替换加载器就宣称数据库已接好。** `prepare_answer_run` 直接调用文件加载器，`_check_snapshot` 读取文件字节哈希，运行元数据保存路径。M5 需要在这条准备路径上接入数据库记录，并对应调整内容身份与元数据；上下文组装、生成、引用守卫和检索算法可继续复用。暂不预建 Repository、通用 storage interface 或移动模块。

- `demo.load_validated_dataset` 当前返回 `(records, payload, reference)`；五类 records 是冻结 dataclass，`payload` 携带来源与审阅状态，`reference` 是 `ReferenceData`。M5 须保留等价信息，完整数据模型以 [数据结构](../../data/CaseTrace_Data_Structure_V2_No_Scenario.md)为准。
- 现有加载路径调用 `validate_relations`、`validate_generation`；来源校验另由 `check_source_records` 执行。换 DB 不能漏掉这些现行检查，也不扩展冻结规则。
- `resolve_query` 按 ID 从文件的 `queries` 读取示例；API 显式 Query 可直接调用核心。数据库示例查询入口如需迁移，一并调整这处适配，不把 Query 变成 Case 字段。
- 文件 SHA-256 当前同时约束语料与主数据。DB 需有可核对的等价内容身份与来源快照映射；继续保留 `known_at` 检查和完整可用性依据，不把 detection_time 当结案时间。
- 迁移检查用固定输入比较原文、实体关系、排名、上下文、Case/Evidence 来源。LLM 输出有非确定性，可回放已保存响应检验应用链路，不要求新调用逐字一致。

## 3. 记录与兼容边界

记录 schema 为 `m4-04-answer-run-2`：保存输入/快照、语料与主数据身份、检索配置/排名、上下文、实际消息、提示词/源码/依赖身份、响应与用量、引用报告和失败信息。凭据从环境变量或项目根 `.env` 加载，环境变量优先；凭据不入产物。

`historical_corrective_action` 是完整历史措施原文、引用 `case.corrective_action`；旧 v1 回放缺字段取 None，不表示 Case 没有措施。v1 没有完整运行源码身份，不能用当前文件补造。批量运行使用新目录，调用前拒绝覆盖旧产物。

当前身份采集依赖源码 checkout 和依赖文件；服务运行路径由 M5 配置，打包部署由 M6 处理。没有通用历史时点过滤能力；模型别名不保证不可变版本。原 v10 两处语义限制、旧 GT 口径与小样本限制见 [当前报告](../../../results/dev-v3-m4-answer-evaluation.md)，均非本次 M5 blocker。
