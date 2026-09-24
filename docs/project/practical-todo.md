# CaseTrace 实操 Todo List

更新日期：2026-09-25。

本文是 [Current Plan](current-plan.md) 的实操阅读版，方便学习和逐项执行；项目范围、正式进度和下一交付以 Current Plan 为准。以下勾选状态是本次整理时的快照。

**当前位置：M2 已验收 accepted（2026-09-22）；M3-01 多方法评估入口已验收 accepted（2026-09-23）；M3-02 Embedding 首次接入已于 2026-09-25 复验 accepted（首轮 5 条 findings 全部关闭）；M3-03 Expand Mock Datasets 已激活、尚未实施，入口见 [M3-03](tasks/m3-03-expand-mock-datasets.md)。执行及验收按 [M3 工作流](../../AGENTS.md#m3-delivery-workflow--user-confirmed-override)。最新状态以 [Current Plan](current-plan.md) 为准；旧归档哈希失败作为非阻塞历史限制保留。**

## 心智模型

CaseTrace 是一个“查历史案例，并带着证据解释”的工具。

```text
输入当前异常 → 找到相关历史案例 → 根据历史证据整理回答
                     ↑
              用人工标准检查找得好不好
```

接下来的重点，就是让“找案例”和“检查找得好不好”完整运行起来。系统提供历史调查参考，不判断当前异常的最终 Root Cause。

## 整体 Todo List

- [x] **数据基础：规定案例怎么存。** 字段、规则、校验器已完成并冻结。
- [x] **异常站点修订：** 按用户确认增加 Case 工序多选、路线并集限制、同站点分组及检索展示；新 benchmark 已在本次最终确认。
- [x] **M1｜能搜索：** 输入异常，BM25 根据词语匹配返回历史案例和来源。真实 demo 和自动回归检查已通过。
- [x] **M2｜能打分：** 你确认哪些案例相关，程序据此评价检索结果。
- [ ] **M3｜比较方法：** 比较 BM25、Embedding（语义搜索）、Hybrid（混合搜索）、Rerank（重新排序），根据结果选方案。四类实验都要完成，Rerank 不必最终采用。
- [ ] **M4｜能解释：** 根据找到的历史记录，回答相关依据、历史原因、历史检查结果和信息缺口，并标出来源。
- [ ] **M5｜接入数据库和接口：** PostgreSQL 保存案例，FastAPI 让网页等程序调用系统。
- [ ] **M6｜完成可展示作品：** Docker、简单网页、最终独立测试、可复现实验和 README。

## 已完成的实操清单：M1 → 第一轮 M2

按下面顺序推进，每完成一项，都应该有一个看得见的结果。

- [x] **1. 修好现有 demo。**

  检查 [demo.json](../../data/dev/demo.json) 中的生产批号，修正样例与 GR-04 的冲突，保留现有规则；补一个直接使用真实 demo 数据的自动检查。

  **完成标志：** 在项目根目录执行 `uv run casetrace demo`，能输出排名、案例 ID 和证据来源。

- [x] **2. 看懂“案例怎样变成可搜索文本”。**

  查看现有 6 个案例各自生成的文本，认识“案例 → 文本 → 分词 → 排序”的过程。确认查询和标注答案没有混入检索文本。

  **完成标志：** 你能拿一个案例，说清楚程序实际搜索了哪些内容。

- [x] **3. 固定迁移后的“小考卷”。**

  使用现有 **6 个历史案例 + 3 条查询**，已保存旧语料快照、原 qrels 及新 [dev-v2 迁移说明](../../data/evaluation/dev-v2/README.md) 和来源哈希。查询文本及时点保持原样。这批全部用于开发，后续独立测试集（Locked Test）另行隔离。

  **完成标志：** 每次评估使用同一份材料，结果可以比较。

- [x] **4. 审阅新版本及 18 个相关性判断。**

  用户已于 2026-09-19 最终确认 dev-v2 数据版本及全部 18 对标签，qrels 已同步为 `human_confirmed`，无需再次确认。源 Case 的审阅状态保持原样。

  **核对结果：** 18 对完整、无重复、无未知 ID，正例数为 4 / 1 / 1；当前 dataset 与主数据哈希匹配。另发现旧版 qrels 归档哈希不一致，详细记录见 [v2 核对记录](../../data/evaluation/dev-v2/README.md)，不能静默刷新哈希。

- [x] **5. 跑出第一份 BM25 成绩单。**

  实现命令行评估，保存每条查询的排名、指标和运行配置，并用可手算的小例子验证计算。主要看：**Recall** 是否漏掉相关案例，**MRR** 第一个相关案例排多前，**nDCG** 相关案例整体是否靠前；辅看 **Precision** 返回结果有多准确。

  **完成标志：** 一条命令能重复得到结果；数据、检索配置和指标口径有版本记录；未标注、不确定和无相关案例的情况有明确处理规则。未标注不能当作不相关。

  **当前小步骤：** 功能 1（读取并校验 `dev-v2/qrels.json`、数据集与主数据）已实现并自测；功能 2 拆为 2A / 2B / 2C，2A（一条 Query 数据流：建一次索引、覆盖全语料的排名、返回 ID 校验、K=1/3/4 与 RR@4 计分）已实现并自测，代码在 [runner.py](../../src/casetrace/evaluation/runner.py)。已讲解，用户 2026-09-21 确认理解；2B（跨 Query 汇总与无正例排除政策）随后实现并自测，汇总入口为同文件中的 `aggregate`，已讲解，用户 2026-09-21 确认；2C（结果保存与 CLI）随后实现并自测：`run_evaluation` 生成含输入哈希、BM25 参数、指标口径、逐 Query 排名与汇总、代码 / 依赖 / git 状态的可复现报告，`write_report` 先写临时文件再原子替换；CLI 新增 `casetrace evaluate`。已讲解，用户 2026-09-22 确认（原话「我已理解 2C」）；再按 [M2 连续完成包](tasks/m2-completion.md) 进入功能 4。功能 4 步骤 A 已把正式结果、日志与运行记录落盘到 `results/`，步骤 B 已写出 [错误分析](../../results/dev-v2-bm25-error-analysis.md)；两个步骤的用户确认为 2026-09-22 原话「4A 和 B 基本理解了」。M2 已最终验收，当前无待交付功能。

- [x] **6. 写第一份简短错误分析。**

  逐条查看：漏了谁、谁排得太靠前、是词语表达问题还是标注问题。只根据实际错误决定要补哪些开发样例。

  **完成标志：** 得到一张“问题 → 可能原因 → 下一步实验”的小表，再进入 M3。数据或标注改变后，各方法需要在同一新版本上重新比较。

## 下一轮怎样衔接

M2 连续实施及教学已收束，完成包作为验收与追溯入口保留。M3 的七个小交付已建包，M3-01、M3-02 已 accepted；**M3-03 Expand Mock Datasets 是当前活动包**。先在包内提出有数量上限的新增 Case / Query 覆盖清单、总配对量和拟用路径，再进入生成；新 Ground Truth 在用户最终确认前保持 draft。以下带日期条目中的小步骤说明是历史快照，最新状态以 [Current Plan](current-plan.md) 与 [M3-03 包](tasks/m3-03-expand-mock-datasets.md) 为准。

以下带日期条目是历史回报，其中待审核状态及曾有的分析错误已由 M2 最终验收与当前分析替代。

## 本次核对记录

2026-09-17 M1 收尾时实际验证：

- `uv run pytest -q`：**119 passed、169 subtests passed**，包含三条真实 Query 的 CLI 回归检查。
- `uv run casetrace demo`：成功输出排名、案例与证据来源；用户已修复此前的批号错误。
- 6 个 Case 均生成非空检索文档；三条 Query 重复运行结果一致，输出来源与原始数据对应。

2026-09-19 异常站点修订实测：`uv run pytest -q` 为 **168 passed、169 subtests passed**；默认 demo 能显示异常工序 ID 和名称，三条真实 Query 的 CLI 回归通过。Excel 保持原样，旧语料及新版本哈希核对通过。

2026-09-19 M2 输入核对：活动 v2 的 ID、18 对标签、Development 范围及两个源文件哈希检查通过；迁移测试实测在旧 qrels 哈希断言失败，问题保留待处理，不宣称全套测试通过。

输入核对时运行 `uv run pytest -q --ignore=tests/evaluation/test_metrics.py`（实际附加 `--tb=short`）得到 **168 passed、169 subtests passed、1 failed**，失败为旧 qrels 哈希检查。交接前加入 RR 后，单独运行 `uv run pytest -q tests/evaluation/test_metrics.py` 实测 **39 passed**；本次未重跑全套测试。

测试通过说明已覆盖的程序行为符合预期；正式检索质量评估属于 M2。当前进入第 5 项的 benchmark 输入校验，后续按连续完成包推进，活动计划以 Current Plan 为准。

本次工作流调整未重跑代码测试；54 passed 为 Cline 在 M2-02 的自测回报，Codex 尚未独立验收。

2026-09-22 M2 功能 3（2C）确认与功能 4（4A、4B）交付（Cline 自测，待 Codex 总审）：

- 2C 确认：用户 2026-09-22 原话「我已理解 2C」，该步骤教学收束。
- 4A 正式运行与结果落盘：新增 `results/dev-v2-bm25.json`（13,460 B）、`results/dev-v2-bm25.cli.txt`、`results/pytest-full.log`、`results/README.md`，README 加运行记录入口并把索引表指向 `results/`。`uv run casetrace evaluate --output results/dev-v2-bm25.json` exit 0；重复运行除 `generated_at` 外完全相等；只读结构性自测 37/37 通过；`uv run casetrace demo` exit 0。未改任何产品代码。
- 4B 错误分析：新增 `results/dev-v2-bm25-error-analysis.md`。三条 Query 在 K=4 **均无漏检**；Q001 同异常分组 G001 位于第 1/2/3 名、仅同产品的 C002 第 4 名，Q002 / Q003 唯一正例第 1 名，符合已记录的阅读期望。机制：本语料 `N=6`、`epsilon=0.25`、`average_idf=0.8373615299`，`idf` 为负时被压到地板 `0.20934038248156323`，df≥4 的词项（`确认` / `检查` / `发现` / `剥离` / `焊线`）几乎无判别力、df=3 恰为 0、只有 df≤2 真正排序；据此记录泛词误召、Query 背景句参与排序、否定语境被计为命中（C002 文本“未发现剥离”仍命中 `焊线` / `剥离`）三类问题，「问题 → 可能原因 → 下一步实验」表五条全部登记为 M3 输入。只读重算自测 174/174 通过。
- 交付读数（观测值，非质量结论）：Q001 `C001 > C003 > C004 > C002 > C005 > C006`；Q002 `C005 > C002 > C006 > C001 > C004`；Q003 `C006 > C005 > C002 > C001 > C004`；汇总 `recall@1 0.75`、`recall@3 0.9167`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5556`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`。
- 交付时复跑：`uv run pytest -q` 为 **277 passed、169 subtests passed、1 failed in 2.21s**（唯一失败仍是既有 dev-v1 归档哈希断言）；`uv run casetrace demo` exit 0。
- 未解决：旧 `dev-v1/qrels.json` 归档哈希差异保留（未刷新哈希、未改旧文件）；`results/dev-v2-bm25.json` 权限 600 记为可选后续项。**M2 交付完毕，标 ready for final Codex review，尚未验收，也未进入 M3。**

2026-09-21 M2 功能 3 / 2C（CLI、结果保存与复现）交付（Cline 自测，待总审）：

- `evaluation/runner.py` 新增 `run_evaluation`（校验输入 → 建一次索引 → 逐 Query 计分 → 汇总 → 可复现报告）与 `write_report`（同目录临时文件 + 原子替换，失败不留半份结果），以及报告常量与私有辅助函数；`casetrace` CLI 新增 `evaluate` 子命令，`--qrels` 默认 `data/evaluation/dev-v2/qrels.json`，`--output` 必填；README 补运行入口与结果说明。未改指标函数、benchmark loader、已确认 qrels、BM25 参数或 demo 行为。
- 报告含：qrels 版本与哈希、dataset / reference 记录路径与实际哈希、split、确认日、dataset 审阅状态、语料最晚发现日、历史快照说明，实际 BM25 参数 `k1=1.5 / b=0.75 / epsilon=0.25`、分词与文档构建入口，K=1/3/4 与 RR 的 K、逐指标公式口径与无正例政策，逐 Query 完整排名 / 分数 / 命中词项，逐指标均值与参与 / 排除清单，以及 Python 与依赖版本、git HEAD、脏工作区路径清单、7 个源码 / 配置文件与 `uv.lock` 的 SHA-256。
- 实测：`uv run pytest -q tests/test_cli_evaluate.py tests/evaluation/test_runner.py` 为 **28 passed**；`uv run pytest -q` 为 **277 passed、169 subtests passed、1 failed**，唯一失败仍是旧 `dev-v1/qrels.json` 归档哈希断言；`uv run casetrace demo` 复跑正常（C001 第 1 名）；`uv run casetrace evaluate --output /tmp/m2-2c-report.json` 成功（13,406 字节）；缺失 qrels 时 exit 2、输出目录无任何文件；两次运行除 `generated_at` 外报告完全相等。
- 该步骤已讲解，待用户确认；下一步功能 4（正式运行、结果文件、简短错误分析与最终回交），详细证据见 [M2 连续完成包](tasks/m2-completion.md)。M2 尚未完成。

2026-09-21 M2 功能 2 步骤 B（跨 Query 汇总与无正例排除政策）交付（Cline 自测，待总审）：

- 在 `evaluation/runner.py` 追加 `aggregate` 与汇总数据类（`ExcludedQuery` / `MetricSummary` / `EvaluationSummary`）及汇总常量；逐 Query 分数按 Query 等权平均，RR@4 的均值命名为 `mrr@4`，与单条 Query 的 `rr@4` 区分。无正例 Query 的 Recall / nDCG / RR 为 `None` 并排除，Precision 的 `0.0` 按函数口径纳入均值；每个指标保存参与 Query 与排除原因，没有参与者时为 `None`（不除零、不写成 0）。未新增文件，未改指标函数、benchmark loader、已确认 qrels 或 BM25 参数。
- 实测：`uv run pytest -q tests/evaluation/test_runner.py` 为 **17 passed**（10 既有 + 7 新增）；`uv run pytest -q` 为 **266 passed、169 subtests passed、1 failed**，唯一失败仍是旧 `dev-v1/qrels.json` 归档哈希断言。真实 dev-v2 观测汇总：`recall@1 0.75`、`recall@3 0.9167`、`recall@4 1.0`、`precision@1 1.0`、`precision@3 0.5556`、`precision@4 0.5`、`nDCG@1/3/4 1.0`、`mrr@4 1.0`，三条 Query 全部参与、无排除。这是当前语料与 BM25 参数下的观测读数，不是检索质量结论。
- 该步骤已讲解，用户于 2026-09-21 回复“理解 下一步”确认；下一步 2C（结果 JSON 复现字段与 `casetrace evaluate` 子命令），详细证据见 [M2 连续完成包](tasks/m2-completion.md)。M2 尚未完成。

2026-09-21 M2 功能 2 步骤 A（一条 Query 数据流）交付（Cline 自测，待总审）：

- 新增 `evaluation/runner.py`（`build_retriever` / `rank_query` / `evaluate_query`，数据类 `RankedCase` / `QueryEvaluation`）与 `tests/evaluation/test_runner.py`，未改动既有文件。请求范围覆盖整个语料，保留 BM25 实际返回的全部条目，拒绝语料之外或重复的返回 ID，再按 K=1/3/4 与 RR@4 计分，无正例时沿用 `None`。
- 实测：`uv run pytest -q tests/evaluation/test_runner.py` 为 **10 passed**；`uv run pytest -q` 为 **259 passed、169 subtests passed、1 failed**，唯一失败仍是旧 `dev-v1/qrels.json` 归档哈希断言；`uv run casetrace demo --json` 正常，默认 top_k=4 的前 4 名与运行器前 4 名一致。真实 dev-v2 观测：Q001 六条全部返回（`C001 5.1445` 起，正例 C001–C004 位于第 1、3、4、2 名），三条 Query 的 Recall@4 / nDCG@4 / RR@4 均为 1.0。这是当前语料下的观测读数，不是检索质量结论。
- 该步骤已讲解，用户于 2026-09-21 确认理解（“基本理解”）；下一会话由 Cline 直接进入 2B（跨 Query 汇总与无正例排除政策）、2C（结果保存与 CLI）；详细证据见 [M2 连续完成包](tasks/m2-completion.md)。M2 尚未完成。

2026-09-20 M2 功能 1 实测：`uv run pytest -q tests/evaluation/test_benchmark.py` 为 **27 passed**；`uv run pytest -q` 为 **249 passed、169 subtests passed、1 failed**，唯一失败仍是旧 `dev-v1/qrels.json` 归档哈希断言；`uv run casetrace demo` 复跑正常。真实 dev-v2 读取实测确认版本、确认日、语料最晚发现日 2026-06-15 与正例 4 / 1 / 1。该功能已自测并讲解，等待用户确认后进入功能 2；详细证据见 [M2 连续完成包](tasks/m2-completion.md)。
