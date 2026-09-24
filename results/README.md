# 评估结果记录（M2 · dev-v2 · BM25）

本目录保存 M2 第一轮 BM25 自动评估的正式产物与运行记录、M3-01 SD4 的 BM25 独立回归结果（见第 8 节），以及 M3-02 首次 Embedding 接入与 BM25 同版本对照（见第 9 节）。这里的内容是**当前语料与参数下的观测读数**，不是已确认的检索质量结论，也不是对真实生产泛化能力的声明。系统提供历史调查参考，不判断当前异常的最终 Root Cause。

## 1. 本次运行

| 项目 | 值 |
|---|---|
| 运行日期 | 2026-09-22（本地，UTC+8）；报告内 `generated_at` = `2026-09-22T05:12:51+00:00` |
| 命令 | `uv run casetrace evaluate --output results/dev-v2-bm25.json` |
| 入口 | [runner.py](../src/casetrace/evaluation/runner.py) 的 `run_evaluation` → `write_report`；CLI 见 [__init__.py](../src/casetrace/__init__.py) |
| HEAD | `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87` |
| 工作区 | **脏（未提交）**；仅 HEAD 不足以复现，必须按第 4 节的源码 / 依赖哈希核对 |
| benchmark | `data/evaluation/dev-v2/qrels.json`，`dev-qrels-v2` / `development` / 确认日 `2026-09-19` |
| 检索 | `rank_bm25.BM25Okapi`，`k1=1.5` / `b=0.75` / `epsilon=0.25`；语料 6 条，请求 `top_k=6`，不补分数、不补名次 |
| 指标口径 | 逐 Query `recall@k` / `precision@k` / `ndcg@k`（K=1,3,4）与 `rr@4`；跨 Query 汇总为 Query 等权平均，RR@4 的均值记作 `mrr@4` |
| 结果 schema | `evaluation-result-v1` |

## 2. 产物

| 文件 | 大小 | SHA-256 | 说明 |
|---|---|---|---|
| `dev-v2-bm25.json` | 14,004 B | `bc457e9576ece6ad29cb2d3991da7c69e939bb4c5a2d0b7330c6039c8441f26d` | 正式结果：逐 Query 完整排名 / 分数 / 命中词项、逐指标分数、汇总与参与 / 排除清单，以及输入、参数与复现信息 |
| `dev-v2-bm25.cli.txt` | 883 B | `f159d812375f4cceb9c0149f430713321527c67582aca4e5baa3668b0ac0ab84` | 同一命令的终端输出（人读）；内容与 JSON 一致，不作为独立来源 |
| `pytest-full.log` | 1,891 B | `57cd01af565fc14b09064cbcd1a7039e186f1c9a60f6dedf7b740efd119f2710` | 本次修订的整套测试输出 |

对这份结果的开发期错误分析（M2 功能 4 步骤 B）见 [dev-v2-bm25-error-analysis.md](dev-v2-bm25-error-analysis.md)：逐 Query K=4 漏检、与已记录阅读期望的对照、命中词项判别力（document frequency）以及「问题 → 可能原因 → 下一步实验」表。该分析只读结果文件与语料，不修改代码、标签或 BM25 参数。

## 3. 读数（观测值）

逐 Query 完整排名（正例来自已确认 qrels，未作任何修改）：

| Query | 正例 | 完整返回排名 |
|---|---|---|
| Q001 | C001、C002、C003、C004 | C001 > C003 > C004 > C002 > C005 > C006（6 条） |
| Q002 | C005 | C005 > C002 > C006 > C001 > C004（5 条） |
| Q003 | C006 | C006 > C005 > C002 > C001 > C004（5 条） |

跨 Query 汇总（三条 Query 全部参与，无排除）：

| 指标 | 值 | | 指标 | 值 |
|---|---|---|---|---|
| `recall@1` | 0.7500 | | `precision@1` | 1.0000 |
| `recall@3` | 0.9167 | | `precision@3` | 0.5556 |
| `recall@4` | 1.0000 | | `precision@4` | 0.5000 |
| `ndcg@1` | 1.0000 | | `mrr@4` | 1.0000 |
| `ndcg@3` | 1.0000 | | `ndcg@4` | 1.0000 |

读数说明：`precision@k` 的分母固定为 k，与该 Query 实际返回多少条无关。Q002 / Q003 各只有 1 个正例，且都排在第 1 名，因此这两条的 `precision@3 = 1/3`、`precision@4 = 1/4` 是口径使然，并不表示前几名排错了；汇总值 0.5556 / 0.5000 被它们拉低。`recall@4 = 1.0` 只说明这 3 条 Query 在 K=4 没有漏掉已确认正例，不代表检索质量已经达标。逐 Query 的漏检、与阅读期望的差距以及误召，是 4B 错误分析的内容。

## 4. 输入与代码版本（复现所需）

输入（报告内哈希 == 磁盘实际字节 == qrels `sources` 记录，自测已核对）：

| 对象 | 路径 | SHA-256 |
|---|---|---|
| qrels | `data/evaluation/dev-v2/qrels.json` | `9112d64cac25e8af0b7b183ca0d083de2c460dc6427cf1c57785f4e0fdfc38b7` |
| dataset | `data/dev/demo.json` | `6923d382ba082f72beb922737e9b169313c1a236662f6a57a8a322e0879689f7` |
| reference | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx` | `f5001bddd3dff43342a2569ceda836ddb4f5c0caca942c1c4d043d99a9131c85` |

代码与依赖（报告 `reproducibility.source_files` 记录值）：

| 文件 | SHA-256 |
|---|---|
| `src/casetrace/__init__.py` | `938fe804e20e46af1e2623bdab439fd991f8d79cbd65d226ec2cd574f10840b5` |
| `src/casetrace/data/constants.py` | `6ceca4b9cd2716b6f960a2022b4bb30de82a6ab9e1de45209d4e6010d1e358fd` |
| `src/casetrace/data/dataset_model.py` | `bace7dba979338725d6bd9e1e58068e5bcc7d37eddc34e8b3fa77e80711f138e` |
| `src/casetrace/data/reference.py` | `6d8e1a3861031698d79519f83f7ee07adcc78ea86883f94370ff71bf92235fa1` |
| `src/casetrace/data/validators.py` | `073297b5957f87b50f490b1abad007bfdc5e6acd823b524980334d01150210cb` |
| `src/casetrace/evaluation/runner.py` | `8c9d89739f334eeddcae4374ca1525ea1cdb0b3fef4568fcb033f1fa2cea8a31` |
| `src/casetrace/evaluation/benchmark.py` | `b18f96ea1e105b52407dec190a7417a8dba7b3289bafe8aeefafd14a57926cb7` |
| `src/casetrace/evaluation/metrics.py` | `47e55310fc9ebf9b4afd406295f6833b2c5cfe7db9ca3e5dbb414464e080d191` |
| `src/casetrace/demo.py` | `27b92bc46db1522ba9e113861bcfb69fdae9fe6d52115e2c91842fe502fa2714` |
| `src/casetrace/retrieval/bm25.py` | `e21e00f76bae8cf6301a94c4e15886326d3f583064fd6df9e71c8859e63523c0` |
| `pyproject.toml` | `a7562713a0afd4e2fef26a137f7790b171f9b30f6cdcbd784a306e65b21517f0` |
| `uv.lock` | `6ae96bf9c5f00a00bff624b644c044a93af40f91579e8f1047215ff62ebbd052` |

运行环境：Python `3.12.3`；`casetrace 0.1.0`、`rank-bm25 0.2.2`、`openpyxl 3.1.5`。

## 5. 复现步骤

```bash
uv sync --locked --inexact
uv run pytest -q                                        # 见第 6 节实际结果
uv run casetrace evaluate --output results/dev-v2-bm25.json
```

- 先比较第 4 节的源码与依赖哈希、以及第 1 节的 HEAD。源码哈希识别运行版本，不是源码备份；复现还需保留对应源码。哈希有变化时先查明原因，不能仅凭 HEAD 判断代码一致。
- 报告写入采用「同目录临时文件 + 原子替换」，失败不会留下半份结果；因此**不要**用 `generated_at` 或运行耗时判断排名是否可重复——它们只说明记录生成时间。
- 只要输入哈希、源码哈希与参数一致，重复运行的排名、分数与指标必须一致（本次已实测，见第 6 节）。
- **注意（M3-01 SD4 追加）：** 本节的命令对应 M2 的 `evaluation-result-v1` 产物。当前源码已升级为 v2（顶层多出 `timing`，见第 8 节），按本节命令重跑会改变该文件的格式与自身 `source_files` 哈希；日常回归请使用第 8 节的产物路径，按字节复现 M2 文件须使用第 4 节记录的源码版本。

## 6. 已跑检查与未跑项

2026-09-22 Codex 复现记录修订（只补源码清单，不调整检索）：

- 回归测试先实测失败，缺少 CLI 和四个数据模块；补清单后 `uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py` → **29 passed**。
- `uv run pytest -q` → exit 1：**278 passed、169 subtests passed、1 failed in 2.32s**。唯一失败仍为 `tests/test_benchmark_migration.py:19` 的旧 dev-v1 归档哈希断言；原始输出见 `pytest-full.log`。
- `uv run casetrace evaluate --output results/dev-v2-bm25.json` → exit 0；重复写至本次临时目录的 `repeat.json`，除 `generated_at` 外完全相等（时间戳允许恰好相同）。`uv run casetrace demo` → exit 0。
- 与修订前结果对照，逐 Query 排名、BM25 分数、命中词项、指标及汇总完全一致；结果中 12 个源码/配置哈希均与当前文件相符。
- 本轮开始前，用户已为 Q001–C004 理由增加“描述均为焊线相关异常，可能存在关联性。此外”，18 对二值标签、Query、语料、确认字段均未改变。新报告如实记录当前 qrels 哈希；这项差异来自用户既有修改，不来自源码清单修复。
- 在临时目录用记录的 HEAD 源码加报告列出的当前源码、输入文件重建：CLI evaluate exit 0，benchmark / retrieval / metrics / queries / summary 与本次报告一致。当前执行中加载的非空 CaseTrace Python 模块均被清单覆盖。这验证本次依赖链，不声称已覆盖未来新增模块或所有运行环境。
- 本次修改前快照、HEAD、Git 状态、隔离重建目录及日志保存在 `/tmp/casetrace-m2-repro-fix-fbr57lij`。初次运行记录与 4A/4B/4C 检查保留在 [M2 完成包](../docs/project/tasks/m2-completion.md)，不将历史通过数冒充本次全部检查通过。
- 未执行 M3/M4 实验；nDCG 已在首次总审及本轮全套测试中覆盖。

## 7. 局限与未解决项

- **不是质量结论**：6 条语料、3 条 Query、单一 BM25 参数，只够支撑「评测流程可用、读数可复现」，不足以说明真实生产表现；不得据此宣称泛化能力。
- **未解决**：`data/evaluation/dev-v1/qrels.json` 的归档哈希与迁移记录不一致（实际 `e92e5bb1f84d…`，记录 `c01752264333…`）。本轮未刷新哈希、未改写旧文件、未猜测标签，失败保持可见；详见 [dev-v2 记录](../data/evaluation/dev-v2/README.md)。
- **工作区未提交**：本次结果对应的是一个未提交工作区，复现必须核对第 4 节哈希；本轮没有 Git 提交或暂存操作。
- **M2 已验收**：两处分析文字已纠正，源码清单缺口已修复；最终 Spec / Standards 结论见 [M2 完成包](../docs/project/tasks/m2-completion.md#2026-09-22-最终验收与交接)。旧归档哈希失败按用户决定作为非阻塞历史限制保留，后续沿用当前 dev-v2；未改旧哈希或失败测试。
- 观察（不影响本次读数）：`dev-v2-bm25.json` 由 `tempfile.NamedTemporaryFile` 创建，权限为 `-rw-------`（600），与目录内其它文件（664）不同。是否调整属于后续可选项，本轮未改动代码。
- 数据校验通过不代表检索标签或检索质量正确；字段展示也不代表已经实现 Grounded Answer。

## 8. M3-01 SD4 独立回归结果（`evaluation-result-v2`，2026-09-23）

M3-01（多方法评估入口）接入 CLI `--method` 后，用当前源码重跑一次 BM25 回归并独立保存，**不覆写 M2 的 `dev-v2-bm25.json`**（该文件仍对应 `evaluation-result-v1`）。本节的读数与第 1～3 节的 M2 读数完全一致，变化只在结果格式（新增耗时记录）。

| 项目 | 值 |
|---|---|
| 运行日期 | 2026-09-23（本地，UTC+8）；报告内 `generated_at` = `2026-09-23T02:19:58+00:00` |
| 命令 | `uv run casetrace evaluate --method bm25 --output results/dev-v2-bm25-m3-01.json` |
| 产物 | `dev-v2-bm25-m3-01.json`，14,741 B，SHA-256 `013738a2d238ecdb01aa0e57295799009ef1160af4f9b3f8236cd6b495f10108` |
| 结果 schema | `evaluation-result-v2`（= v1 + 顶层 `timing`） |
| 输入与口径 | 与 M2 相同：同一 `data/evaluation/dev-v2/qrels.json`（`dev-qrels-v2` / `development`）、同一 BM25 参数（`k1=1.5` / `b=0.75` / `epsilon=0.25`）与分词、同一 K=1/3/4 与 `rr@4` / `mrr@4` 口径 |
| 排名与读数 | 与第 3 节逐项相同：Q001 `C001 > C003 > C004 > C002 > C005 > C006`、Q002 `C005 > C002 > C006 > C001 > C004`、Q003 `C006 > C005 > C002 > C001 > C004`；`recall@1 0.7500`、`recall@4 1.0000`、`mrr@4 1.0000`（其余同第 3 节） |

### 8.1 格式变动（v1 → v2）与对照结论

- **唯一新增顶层 `timing`**；其余顶层键的名称、数量与内容口径不变。
- 只读脚本逐字段对照 M2 正式结果：`benchmark`、`retrieval`、`metrics`、`queries`、`summary` 五个面板**全部一致**（含逐 Query 完整排名、BM25 分数、命中词项与全部指标与汇总）。因此格式升级没有改变任何事实字段。
- `reproducibility.source_files` 如实变化：新增 `src/casetrace/retrieval/base.py`；`src/casetrace/__init__.py`、`src/casetrace/evaluation/runner.py`、`src/casetrace/retrieval/bm25.py` 的哈希随 M3-01 实现更新。这不属于读数差异。

### 8.2 `timing` 的内容与测量边界

| 字段 | 本次读数 | 覆盖范围 |
|---|---|---|
| `index_build_seconds` | 0.00195 s | 历史检索文本构建 + 检索器构造（建索引）；不含输入校验、逐 Query 计分与报告组装 |
| `per_query[].seconds` | Q001 0.00037 / Q002 0.00026 / Q003 0.00022 s | 该 Query 的检索、返回 ID 守卫与指标计算（qrels 只在此步进场）；按 Query 顺序逐条计分，不并发 |
| `queries_total_seconds` | 0.00085 s | 上面三条之和 |
| `total_seconds` | 0.02311 s | 进入 `run_evaluation` 到跨 Query 汇总完成；不含复现字段的 git 查询与文件哈希、写文件与终端输出 |

- 时钟为 `time.perf_counter`（单调，不受系统时间调整影响），单位为秒；报告内同时写明 `boundaries` 与 `comparison_note`，读者不必猜每个数字包住了哪一步。
- **耗时与 `generated_at` 不参与确定性比较**：比较排名、分数与指标时必须忽略这两个字段。单次读数不足以评价方法效率；同版本方法比较耗时需固定硬件、冷启动与缓存条件并重复测量。

### 8.3 已跑检查与未跑项

- 全套测试：`uv run pytest -q` → **289 passed、169 subtests passed、1 failed**；唯一失败仍是 `tests/test_benchmark_migration.py:19` 的旧 dev-v1 归档哈希断言（既有历史限制，与本次无关）。
- 定向测试：`uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py tests/retrieval/test_bm25.py tests/test_demo.py` → **60 passed**；其中确定性比较已按 v2 改为剔除 `generated_at` 与 `timing`，并新增 `timing` 形状与"耗时不得进入 metrics / queries / summary"的回归。
- `uv run casetrace demo` → exit 0；`uv run casetrace evaluate --method bm25 --output results/dev-v2-bm25-m3-01.json` → exit 0（终端首行含 `检索方法：bm25_okapi`）。
- 重复运行实测：同一输入连续两次运行，`benchmark` / `retrieval` / `metrics` / `queries` / `summary` 完全一致；仅 `generated_at`、`timing.*` 变化，另有 `reproducibility.git_status_paths` 多出一项 `results/dev-v2-bm25-m3-01.json` —— 第 1 次运行发生在该产物文件存在之前，第 2 次运行时它已在工作区，属如实记录执行时点的工作区状态，不是排名或分数差异。
- 本产物自身的 `reproducibility.git_status_paths` **不含** `results/dev-v2-bm25-m3-01.json`（生成时该文件尚未写入），与 `write_report`「先写临时文件再原子替换」的顺序一致。
- 未跑：Embedding / Hybrid / Rerank 实验（M3-02 起）、Locked Test 对比（M6）。
- 权限观察（沿用第 7 节记录）：本文件由 `write_report` 的临时文件创建，权限为 `-rw-------`（600），与目录内其它文件（664）不同；是否调整仍属后续可选项，本轮未改代码。

## 9. M3-02 首次 Embedding 结果与 BM25 同版本对照（`evaluation-result-v2`，2026-09-24）

M3-02 在 M3-01 的入口上首次接入语义检索，并在同一 dev-v2 上重跑 BM25 作为对照。**不覆写** M2 的 `dev-v2-bm25.json` 与 M3-01 的 `dev-v2-bm25-m3-01.json`。
2026-09-25（本地）按 Codex findings 修正后重新生成过这两份产物（缓存键补入依赖版本与 dtype、报告文案更正），排名、分数与指标逐位未变，哈希以下表为准；改了什么见 [9.3](#93-codex-findings-修正轮2026-09-25本地)。

| 项目 | BM25（对照） | Embedding（首次接入） |
|---|---|---|
| 命令 | `uv run casetrace evaluate --method bm25 --output results/dev-v2-bm25-m3-02.json` | `uv run casetrace evaluate --method embedding --output results/dev-v2-embedding-m3-02.json` |
| 产物 | `dev-v2-bm25-m3-02.json`，15,520 B，SHA-256 `df2c2f5d218bc55328483116fec06f11799176b20dfd0eb32cbc8883dd9c0e06` | `dev-v2-embedding-m3-02.json`，15,773 B，SHA-256 `98aaf6e95971a28f81c8a3fc12f08acf3bfce15d4c63e7a66af70a4e5b054ab0` |
| `generated_at` | `2026-09-24T16:05:02+00:00` | `2026-09-24T16:04:55+00:00` |
| 检索实现 | `rank_bm25.BM25Okapi`（`k1=1.5` / `b=0.75` / `epsilon=0.25`；分词未变） | `BAAI/bge-small-zh-v1.5` @ revision `7999e1d3…`；CPU / float32；Query 加 instruction、文档不加；逐行 L2 归一化后点积；`max_seq_length=512`（未触发截断）；`retrieval.libraries` 记录 numpy 2.5.3 / sentence-transformers 6.1.0 / transformers 5.17.0 / torch 2.14.0+cpu |
| 缓存条件 | 无 | **hit**：`.cache/embeddings/d2374a3b295754f151002b8e3d5b38613c169700f6c3bed1e2e7727ab0464497.json`，68,640 B，SHA-256 `388ef8d1f6519cdb5fd99617a5bf15c0c247a60cc24ee9f4f3a34a5373e3d4a0`（该目录已被 `.gitignore` 忽略；同目录仍留有 SD4 时点的旧键 `0fcdd55f….json`，键已不匹配、不再被使用） |
| 结果 schema | `evaluation-result-v2` | `evaluation-result-v2`（额外含 `timing.method_details` 与 `retrieval.cache`） |
| HEAD / 工作区 | `b8aaea4151b74d4b2bf80255a5cc22b5105a7205` / 脏（未提交） | 同左 |

读数（观测值，非质量结论；正例来自已确认 qrels，未作修改）：

| Query | BM25 | Embedding |
|---|---|---|
| Q001（4 正例） | C001 > C003 > C004 > C002 > C005 > C006 | C001 > C003 > C004 > C006 > C005 > C002 |
| Q002（1 正例） | C005 > C002 > C006 > C001 > C004 | C005 > C004 > C001 > C003 > C006 > C002 |
| Q003（1 正例） | C006 > C005 > C002 > C001 > C004 | C006 > C004 > C002 > C001 > C003 > C005 |

汇总对照：`recall@1` 0.7500、`recall@3` 0.9167、`precision@1` 1.0000、`precision@3` 0.5556、`ndcg@1` / `ndcg@3` 1.0000、`mrr@4` 1.0000 **两者相同**；差异只在 K=4：`recall@4` 1.0000 → 0.9167、`precision@4` 0.5000 → 0.4167、`ndcg@4` 1.0000 → 0.9440，全部来自 Q001 的同产品正例 C002 由第 4 名降到第 6 名。

耗时（修正轮重生成时的观测值，不可作效率结论）：BM25 `index_build 0.0017 s` / `total 0.0210 s`（逐 Query 0.0003 / 0.0002 / 0.0002 s）；Embedding `hit` 时 `index_build 4.6685 s`（模型加载 4.6644 s + 文档编码 0 s + 缓存读取 0.0012 s）/ `total 4.7198 s`（逐 Query 0.0128 / 0.0095 / 0.0089 s）；同一环境改用独立缓存目录做 `miss` 对照：模型加载 4.7662 s + 文档编码 0.2052 s，`index_build 4.9823 s` / `total 5.0320 s`（逐 Query 0.0106 / 0.0092 / 0.0099 s）。硬件为 i7-8550U / 31 GB，全程 CPU 与离线（`local_files_only=True`）。

完整对照、机制观察与「问题 → 下一步实验」见 [dev-v2-bm25-vs-embedding-m3-02.md](dev-v2-bm25-vs-embedding-m3-02.md)。

### 9.1 数值复现条件（实测）

- 重复运行（BM25 两次、Embedding 两次）：`benchmark` / `retrieval` / `metrics` / `queries` / `summary` 五个事实面板**完全一致**；只有 `generated_at`、`timing.*` 与 `reproducibility.git_status_paths` 变化。后运行的那次会多出**先写出的结果文件本身**（本对照 27 → 28 条），属如实记录执行时点的工作区状态。2026-09-25 修正轮重生成时复测仍然成立（正式产物与 `/tmp` 重复运行五面板逐项相等，见 9.3）。
- **缓存 `hit` 与 `miss` 不是逐位相同**：排名顺序与全部汇总指标一致，分数的末位浮点差逐 Query ≤ 3.331e-16。成因是缓存行范数不是精确 `1.0`（实测 `0.9999999999999999` 与 `1.0000000000000002`），读取时会再归一化一次。因此「缓存只影响耗时不影响结果」**仅在排名与指标层面成立**，这一点已写进对照分析。
- Embedding 的模型权重位于 HuggingFace 缓存（`~/.cache/huggingface/…`），与本项目的向量缓存是两套东西；约 4.8 s 的模型加载无法由本项目缓存省掉。

### 9.2 已跑检查与未跑项

- 全套测试：`uv run pytest -q` → **320 passed、169 subtests passed、1 failed**；唯一失败仍是 `tests/test_benchmark_migration.py:19` 的旧 dev-v1 归档哈希断言（既有历史限制，不归因于 M3-02）。比首轮验收时的 315 passed 多 5 例，即修正轮新增的缓存键与损坏缓存的回归用例。
- 定向测试：`uv run pytest -q tests/retrieval/test_embedding.py tests/evaluation tests/test_cli_evaluate.py tests/test_demo.py` → **164 passed**。
- `uv run casetrace demo` → exit 0（demo 仍只跑 BM25）；两条 `evaluate` 命令 → exit 0；`uv run casetrace evaluate --method hybrid --output /tmp/…` → **exit 2 且不留文件**（未知方法不落盘）。
- 未跑：Hybrid（M3-04）、Rerank（M3-05）、针对性参数实验（M3-06）、Locked Test 对比（M6）。
- 权限观察：两个新产物权限同为 `-rw-------`（600），与既有产物一致，本轮未改代码。

### 9.3 Codex findings 修正轮（2026-09-25 本地）

首轮 Codex 验收为 **needs changes**（Spec 2 项 + Standards 3 项）。修正轮只动缓存键、缓存读取的容错与自描述文案，**没有改检索算法、参数、标签与指标口径**：

| finding | 修正 | 证据 |
|---|---|---|
| Spec ① 缓存键未绑定依赖版本与 dtype | `EmbeddingRetriever._encoding_config()` 增加 `libraries`（numpy / sentence-transformers / transformers / torch）、`model_output_dtype`、`working_dtype`；三者之外的既有字段不变 | 快照对照：旧 config 无这三项，新 config 含 `{'numpy': '2.5.3', 'sentence-transformers': '6.1.0', 'transformers': '5.17.0', 'torch': '2.14.0+cpu'}`；新增回归 `test_cache_config_records_dependency_versions_and_dtypes`、`test_dependency_version_change_invalidates_cache` |
| Spec ② 合法 JSON 但 `vectors` 类型非法时抛未捕获 `TypeError` | `_read_cache()` 的向量转换改为捕获 `(TypeError, ValueError, OverflowError)`，一律判 `corrupt` 并重新编码 | 快照对照：旧实现抛 `TypeError: float() argument must be a string or a real number, not 'dict'`；新实现 `status=corrupt`、写明原因并重新编码（`test_valid_json_with_invalid_vector_payload_is_corrupt`，3 组非法内容） |
| Standards ① 缓存 note 与实测不符 | `describe().cache.note` 改为「不改变排名与指标；命中缓存的向量经 JSON 往返与再次归一化，可能有末位浮点差（M3-02 实测 ≤3.331e-16）」 | 新产物 `retrieval.cache.note` 即该文案 |
| Standards ② 耗时细分字段路径写错 | `TIMING_BOUNDARIES` 改为「细分见顶层 `timing.method_details`」 | 新产物 `timing.boundaries[0]` 已更正 |
| Standards ③ 包头与 SD2 状态文字过期 | 任务包头、SD2 表格与状态行统一为「已完成 / 待复验」 | [M3-02 包](../docs/project/tasks/m3-02-embedding.md) |

修正后重生成（命令见上表；Embedding 先跑一次 `miss` 写入新键，再跑一次 `hit` 作为正式产物）：

- 旧产物（SD4 时点）→ 新产物：BM25 `e953e772…5910`（15,373 B）→ `df2c2f5d…0e06`（15,520 B）；Embedding `8450bb5b…6856`（15,482 B）→ `98aaf6e9…4ab0`（15,773 B）。M2 `bc457e95…f26d` 与 M3-01 `013738a2…0108` 仍未覆写。
- 与 SD4 时点产物逐面板比较：`benchmark` / `metrics` / `summary` **完全相等**；`queries` 排名顺序一致、分数最大 `|Δ| = 0.000e+00`；差异只在 `retrieval`（新缓存键、`libraries` 四项、note 文案）与 `timing`（新耗时、boundaries 文案）。
- 新缓存文件 `d2374a3b….json`（68,640 B，SHA-256 `388ef8d1…e4a0`）由本次 `miss` 运行写出，正式产物为同键 `hit`；SD4 时点的 `0fcdd55f….json`（68,463 B）保留为派生数据，键已不匹配、不再被使用。
