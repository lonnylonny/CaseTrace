# dev-v3 版本说明与确认记录

本目录保存 Development 新版本的 qrels 及其确认记录。**当前状态：全部 45 对保持 `human_confirmed`；2026-09-26 用户更正 Q001×C007 为 Relevant，当前为 qrels revision 2。**

| 项目 | 值 |
|---|---|
| 语料 | [data/dev/demo-v3.json](../../dev/demo-v3.json)，`dev-corpus-v3`，9 Case / 9 Detail / 9 Evidence / 5 Query |
| 语料 SHA-256 | `0a29041a4e6ed11a5b31ff85a74fa8bed9b79afeb1d35158ea9430f6e5af8f0b` |
| qrels | [qrels.json](qrels.json)，`dev-qrels-v3`，`human_confirmed`（初次确认 2026-09-25，更正 2026-09-26），45 对，revision 2 |
| qrels SHA-256 | `7c4e85511ba72b58b19eb3134f1935c711e0f3142e58ba118918d96afac7b4dd` |
| 主数据 | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx`，`f5001bdd…1c85` |
| 前身 | [dev-v2](../dev-v2/README.md)（6 Case × 3 Query、18 对用户已确认标签、M2 / M3-01 / M3-02 正式结果） |

dev-v2 语料、dev-v2 qrels 与既有正式结果**保持原字节**，属于旧版本。两版指标不得互相比较，也不得跨版本宣称提升。

## 2026-09-25 Query 补足

用户指出原 Query 只有异常描述，缺少客户、产品与批号，而检索语料（`build_documents`）已索引 `product_id`、`product_name`、`package_route`、`production_lot`、`customer_lot`，两侧不对称会削弱尤其是 Hybrid 的词面信号。本次按用户决定补足**全部 5 条 Query**。

规则：**每条 Query 写明当时已知的客户、产品、生产批号与客户批号；取值必须与主数据及语料一致。**

| Query | 产品 | 产品族 / 路线 | 客户 | 生产批 | 客户批 | 批号来源 |
|---|---|---|---|---|---|---|
| Q001 | PROD_001 | PF_001 / LF_WB | CUS_001 | DEV_PL_001 | DEV_CL_001 | 复用：语料中属 C001、C002 的批 |
| Q002 | PROD_013 | PF_007 / LF_WB | CUS_001 | DEV_PL_012 | DEV_CL_012 | 新生成 |
| Q003 | PROD_006 | PF_003 / SUBSTRATE_WB | CUS_004 | DEV_PL_013 | DEV_CL_013 | 新生成 |
| Q004 | PROD_009 | PF_005 / SUBSTRATE_WB | CUS_003 | DEV_PL_009 | DEV_CL_009 | 复用：语料中属 C008 的批 |
| Q005 | PROD_004 | PF_002 / LF_WB | CUS_002 | DEV_PL_014 | DEV_CL_014 | 新生成 |

匹配依据与边界：

- 客户由产品经 `customer_product_map` 推导（CR-04：产品唯一确定客户）；Query 的客户不能自由指定。
- 复用的两个批号与语料完全一致：同产品、同投批时间、同客户批（CR-08～CR-10）。例如 `DEV_PL_001` 在语料中属 PROD_001、投批 2026-06-01、客户批 `DEV_CL_001`。
- 三个新批号 `DEV_PL_012～014` 与 `DEV_CL_012～014` 未与任何既有 Case 重复，代表当前 Incident 自身的新批，**不进入历史 Case**。
- 批号是**模拟值**，主数据 Excel 没有批号表；可核对的是"产品 ↔ 客户"与"复用批号 ↔ 语料记录"的一致性。
- 客户标识目前**不在语料文档索引中**（`build_documents` 未拼接客户），因此客户进 Query 用于还原当时已知事实与可追溯性，不产生词面匹配。若要客户参与检索，需要单独决定是否改动语料文本。
- 可重复核对的脚本：`uv run python scripts/check_query_enrichment.py`（只读，校验产品存在、客户推导、复用批号一致性、标识数量）。

语料中记录的 `query_revision` 字段保存本次补足的说明、规则与批号来源；该字段与查询、来源元数据一样不进入检索文本。

## Ground Truth 确认记录

用户于 **2026-09-25** 通过分级标注矩阵（`dev3groundtruth.xlsx`，原始矩阵快照保存在本地开发记录备份）对 dev-v3 全部 45 对作出判断，`qrels.json` 已发布为 `human_confirmed`，`confirmation_scope = dev_v3_query_enriched_corpus_and_all_45_binary_labels`。

**2026-09-25 用户原始标注（逐格原文，保留历史；当前标签另见下方修订）：**

| Case | Q001 | Q002 | Q003 | Q004 | Q005 |
|---|---|---|---|---|---|
| C001 | 最强相关 | 无关 | 无关 | 无关 | 强相关 |
| C002 | 同产品同批次有参考价值，但是不相关 | 无关 | 无关 | 无关 | 无关 |
| C003 | 同异常，相关性强，但发现站点不同，产品和批次也不同，弱于C001 | 无关 | 无关 | 无关 | 强相关 |
| C004 | 相似异常，关联性低于C003，但高于002 | 无关 | 无关 | 无关 | 弱相关 |
| C005 | 完全无关 | 强相关 | 无关 | 强相关，同异常 | 无关 |
| C006 | 完全无关 | 无关 | 强相关 | 无关 | 无关 |
| C007 | 完全无关 | 无关 | 无关 | 无关 | 最强相关 |
| C008 | 完全无关 | 强相关 | 无关 | 最强相关，同异常同产品同批次 | 无关 |
| C009 | 完全无关 | 无关 | 都为锡球，很弱关联 | 无关 | 无关 |

**二值口径（用户确认）：** 最强相关 / 强相关 / 弱相关 → Relevant；很弱关联 / 无关 / 完全无关 → Not Relevant。分级只作阅读顺序参考，**不进入指标、不转换为权重**（业务与评估约定 §2）。

**2026-09-25 四点裁决与当时落库结果（第 3 项已由 2026-09-26 修订取代）：**

| # | 相关配对 | 用户说明 | 落库标签 |
|---|---|---|---|
| 1 | `Q001×C002` | 异常本身不相关，但因同产品同批次应被找到 | 1（Relevant） |
| 2 | `Q003×C005` | 更正为相关（类似产品 PF_003） | 1（Relevant） |
| 3 | `Q001×C007` | 共享 `failure_mode_id` 只是极弱约束，异常本身完全不同，二值下接近 0.01 级 | 0（Not Relevant） |
| 4 | `Q005×C004` | 确认应为相关，原 `needs_user_ruling` 结案 | 1（Relevant） |

历史说明：第 3 点曾由 Cline 对应到 `Q001×C007` 并落为 0。用户已于 2026-09-26 明确更正该误判；不再使用“只共享 failure_mode_id、异常不同”解释此配对。

**初次确认相对草稿的两处变化（历史）：** `Q001×C007` 1 → 0、`Q005×C004` 0 → 1。其余 43 对标签不变，理由文本按新 Query 事实与本次裁决更新。

**当前正例数：** Q001 / Q002 / Q003 / Q004 / Q005 = **5 / 2 / 2 / 2 / 4**（共 15）。全部 45 对 `origin = user_confirmed`。

**与现行规则的对照（如实记录，不阻塞本版）：** 「同产品同批次」（`Q001×C002`）与「仅同产品族」（`Q003×C005`）经用户确认仍为 Relevant；同时用户提出「同产品本身是极弱约束」。这些背景充分条件属于旧口径，与现行业务与评估约定 §2 有差异；本版按用户逐对判断保留，不自动重标。

## 2026-09-26 用户更正（qrels revision 2）

用户在 Codex 验收指出两处冲突后明确要求：“1.修正 2.这个是我判定错误，请修改，我有和cline提过可能遗漏了，你再检查一遍”。据此执行：

- **Q001×C007：0 → 1。** 焊线/焊点自焊盘脱开与键合金球自焊盘界面分离是该样例的同义异常表述；依据用户更正与实际表现判为 Relevant，不依赖共同 failure_mode_id，也不要求历史原因相同。
- **Q005×C004：标签保持 1，修正理由。** C004 是第二焊点颈部断裂、pad 界面完整，不能写成键合界面断裂。保留用户的弱相关裁决，不把共用 failure_mode_id 解释成自动相关规则。
- 其余 44 对标签、全部 Case / Query 及检索代码保持不变。用户更正发生于验收发现后，未按模型输赢选择标签。
- 原 qrels 按字节保存在 [archive/qrels-2026-09-25.json](archive/qrels-2026-09-25.json)，SHA-256 `bd34f2c0ae0462ec868d096da3ebdb2e779d8fe6b8c29ac5447d1ea11a01d942`。原始分级矩阵及初次裁决保留为历史，不再表示当前标签。
- `qrels_version = dev-qrels-v3` 表示原有支持版本，新增 `qrels_revision = 2` 和修订历史；正式结果以原字节 SHA-256 区分修订。当前两条结果均为 `*-m3-03-r2.json`，不得混用 r1/r2 的指标。

## 来源、家族与语义审阅记录

**生成依据：** `generation_basis` 记录 GR-10——产品、工序、批号、时间、数量、原因与措施候选由 Python 从主数据确定，只改写文本字段。`supersedes` 指向 [data/dev/demo.json](../../dev/demo.json)（`6923d382…89f7`），dev-v2 语料保持原字节。

**逐 Case 来源：** `sources` 保存每条 Case 的来源工作表与匹配字段（`sheet = failure_modes`、`failure_mode_id`、`root_cause`、`corrective_action`、`closure_status = confirmed`）。新增三条另带 `generation_note`：

| Case | failure_mode_id | 家族 | 同义父项 | 覆盖缺口（用户已确认的清单） |
|---|---|---|---|---|
| C007 | 00010 | `wire-bond-lift(00010)` | C001 | 同义表达 + 技术类比（跨产品族、跨路线）；Q001×C007 已由用户更正为相关 |
| C008 | 00018 | `molding-void(00018)` | — | 技术类比（跨产品族、跨路线）；`production_lot` 供 Q004 的同批次背景联系 |
| C009 | 00028 | `ball-damage-confusable(00028 vs 00026)` | — | 易混淆（探针压形 vs 运输碰伤）与 Evidence 否定表达 |

**近重复家族（`case_families`，供 M6 隔离）：** `wire-bond-lift(00010)` = C001 / C003 / C004 / C007（C007 的异常描述以 C001 为措辞父项；用户已更正为同异常相关，历史原因并不相同）；`molding-void(00018)` = C005 / C008；`ball-damage-confusable(00026 vs 00028)` = C006 / C009（表面相似、机制不同，记为易混淆对而非近重复）。**家族关系不构成检索相关性。**

**语义审阅范围（如实记录，未自动化的部分不宣称已覆盖）：**

- 已由确定性检查覆盖：版本与哈希绑定、ID 唯一、Query × Case 完整配对、确认状态与 Development 守卫、时点一致性（`tests/evaluation/test_benchmark.py`；Query 取值一致性 `scripts/check_query_enrichment.py`）。
- 已记录的用户判断：全部 45 对二值标签及相关逐对裁决；2026-09-26 明确更正 Q001×C007 的同义异常相关性。覆盖表同时记录生成目的，标签确认不代表全部 Case / Evidence 语义检查完成。
- **未自动化的语义边界：** 同义异常、易混淆对及弱相关边界依赖逐对人工判断，不由 Validator 或来源家族自动推出；本版已记录的裁决见上节。未记录的完整语义审阅不宣称完成，源 Case 的 draft 状态保留。
- 源 Case 的 `review_status` 仍为 `draft_pending_human_review`，不因 qrels 确认而改变。

## 当前正式结果（2026-09-26，qrels revision 2）

两方法使用同一修订后的 qrels（5 / 2 / 2 / 2 / 4 正例）与未改动的语料/Query，固定原模型与参数重新运行，均 exit 0：

```bash
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method bm25 --output results/dev-v3-bm25-m3-03-r2.json
uv run casetrace evaluate --qrels data/evaluation/dev-v3/qrels.json --method embedding --output results/dev-v3-embedding-m3-03-r2.json
```

| 方法 | 当前结果 | 终端附件 | 索引构建 | 逐 Query 合计 |
|---|---|---|---|---|
| bm25 | [JSON](../../../results/dev-v3-bm25-m3-03-r2.json) | [CLI](../../../results/dev-v3-bm25-m3-03-r2.cli.txt) | 0.003 s | 0.001 s |
| embedding | [JSON](../../../results/dev-v3-embedding-m3-03-r2.json) | [CLI](../../../results/dev-v3-embedding-m3-03-r2.cli.txt) | 4.239 s | 0.182 s |

Embedding 命中既有文档向量缓存，索引构建仍含模型加载；计时为本机单次读数，不支持效率结论。运行时间分别为 2026-09-26T09:35:05+00:00 / 2026-09-26T09:35:10+00:00。

| 指标 | bm25 | embedding |
|---|---|---|
| Recall@1 / @3 / @4 | 0.3900 / 0.6700 / 0.8600 | 0.3900 / 0.7700 / 0.8600 |
| Precision@1 / @3 / @4 | 1.0000 / 0.6000 / 0.6000 | 1.0000 / 0.7333 / 0.6500 |
| nDCG@1 / @3 / @4 | 1.0000 / 0.8165 / 0.8871 | 1.0000 / 0.9226 / 0.9226 |
| MRR@4 | 1.0000 | 1.0000 |

| Query | bm25 命中 / 正例 | bm25 漏掉（名次） | embedding 命中 / 正例 | embedding 漏掉（名次） |
|---|---|---|---|---|
| Q001 | 4 / 5 | C007（6） | 4 / 5 | C002（5） |
| Q002 | 2 / 2 | — | 2 / 2 | — |
| Q003 | 2 / 2 | — | 1 / 2 | C005（8） |
| Q004 | 2 / 2 | — | 2 / 2 | — |
| Q005 | 2 / 4 | C003（8）、C004（5） | 4 / 4 | — |

**修订影响与比较边界：** 两方法各自的全部排名与修订前完全一致，改变的是相关标签和计分。Q001 新增第 5 个正例后，两方法前四名均命中 4/5；BM25 漏 C007（第 6），Embedding 漏 C002（第 5）。本次指标变化不能解释成算法提升或退步。Q001 有 5 个正例，所以 Recall@4 即使前四名全部相关也最多为 0.8。

只在相同语料、Query、qrels **revision/hash** 与指标口径下比较方法；不与 dev-v2 或 dev-v3 r1 混比。5 条 Query 不支持泛化结论；原始分数跨方法不可比较。源码、配置、完整排名及耗时边界以 JSON 为准。

**历史结果（r1，仅存档）：** [BM25](../../../results/dev-v3-bm25-m3-03.json) / [Embedding](../../../results/dev-v3-embedding-m3-03.json) 绑定修订前 qrels `bd34f2c0…d942`，原文件未覆盖。旧 Recall@4 = 0.90 / 0.85 已不代表当前标签。Cline 的旧冷暖复核记录只适用于 r1，未冒充 r2 的新冷启动实验。

## 快照约定与边界

- 九条 Case 的完整内容被设定为在 2026-09-15 之前已结案且可供查看（沿用 dev-v2 的同一模拟快照时点），九条 Detail 的 `detection_time` 均不晚于该时点。这是模拟约定，不代表已实现通用结案／可用时间过滤。
- 数据集 `split = development`，`review_status = draft_pending_human_review`；源 Case 的审阅状态不因 qrels 确认而改变。
- 已知历史限制：`data/evaluation/dev-v1/qrels.json` 的归档哈希不一致，按用户决定不阻塞开发，与本版无关。
