# locked-test-v1 版本说明与审阅记录

状态：**已冻结（SD1～SD5 完成，2026-10-08）。**
本目录保存 Locked Test 的正式 qrels、草稿、比较协议与审阅记录；协议身份已在 [protocol.md](protocol.md) §6 标注 frozen。
按用户决定（2026-10-08），后续只用已选固定方案 **R3** 运行一次以确认评估链路，不做多方法对比；
运行记录与限制见 [results/locked-test-v1/](../../../results/locked-test-v1/README.md)。

| 项目 | 值 |
|---|---|
| 语料 | [data/locked-test/corpus-v1.json](../../locked-test/corpus-v1.json)，`locked-test-corpus-v1`，9 Case / 9 Detail / 19 Evidence / 5 Query |
| 语料 SHA-256 | `2fdc390ac65eb023acf7d9e77388321dd5479187dbd27ab11c1d5d58284def18` |
| qrels 草稿 | [qrels.draft.json](qrels.draft.json)，`locked-test-qrels-v1`，45 对建议标签，保留为裁决前历史 |
| qrels 草稿 SHA-256 | `f5a009ca8cb10a22e02084e2afcb6f9ff5856f6c397547fe0d096e1e6a88f01e` |
| **正式 qrels** | **[qrels.json](qrels.json)**，`locked-test-qrels-v1`，`human_confirmed`，2026-10-08，45 对 0/1 |
| **正式 qrels SHA-256** | `d6ad943390f9b7136fac60f5dc73c0d9d7c62e8623836a32d7bc2f82c9b93540` |
| 协议 | [protocol.md](protocol.md)（SD1 预登记；SD5 冻结内容身份） |
| 生成入口 | [scripts/prepare_locked_test_v1.py](../../../scripts/prepare_locked_test_v1.py)（确定种子 `20260831`，不调用模型服务） |
| 主数据 | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx` |

Development 语料与 qrels 保持原字节，**与本集合不可互相比较**。

## 覆盖与家族

**规模：9 Case / 9 Detail / 19 Evidence（每 Case ≥2）/ 5 Query / 45 个完整配对。**
LC003 为双异常（die tilt + package warpage），其余 8 个 Detail 单异常，比例约 11% / 89%，符合 GR-02。
CaseGroup / Membership 为空；家族只写进语料元数据，不建业务 Group。

| 家族 | Case | 说明 |
|---|---|---|
| `geometry-tilt-warpage` | LC001～LC005 | die tilt 与 package warpage；整族仅用于 Locked Test |
| `fc-bump-open-short` | LC006～LC009 | FC bump open 与 bump short；整族仅用于 Locked Test |

**家族关系不构成检索相关性。**

## 隔离依据

- 本轮核对两份开发语料：已用来源为 `00010 / 00016 / 00018 / 00026 / 00028`；
  新四条来源 `00004`（die tilt）/ `00022`（package warpage）/ `00030`（bump open）/ `00031`（bump short）与它们不重合。
- 新 Case 产品取 `PROD_007/008/010/012/014/016/017`，均未出现在开发 Case 或开发 Query 中；
  die tilt 与 warpage 用基板/框架路线，bump open/short 用 `SUBSTRATE_FC`，与来源适用范围一致。
- 逐案比较了实际异常表现、来源、措辞父项与机制：新文本以已确定事实重写，
  开发 Case / Query 不是新文本的改写父项；未混入 wire bond lift、molding void、lead solderability、BGA ball damage 的改写。
- 共享冻结主数据与通用术语是允许的。**这是同一合成知识底座下的来源/家族隔离，小样本不证明真实现场泛化。**

## 批号、时点与模拟快照

- 新批号沿用 `DEV_PL_` / `DEV_CL_` 格式，从 101 起编号；前缀不决定 split。
- Case 批号 `DEV_PL_101`～`DEV_PL_108`。整份语料只复用 **1 个生产批 `DEV_PL_102`**（出现 2 次：
  LC002 与 LC005，同产品 PROD_007、同投批时间 2026-06-10、同客户批 DEV_CL_102，符合 GR-04）。
- 五条 Query 的当前批：`DEV_PL_109`～`DEV_PL_112` 为新批；**LQ003 复用历史批 `DEV_PL_102`** 作已知背景，
  与语料中该批的产品、投批时间、客户批一致。同批背景不自动产生正例。
- 历史投批 2026-06-01～2026-07-31，发现/反馈为投批后至 2026-08-20。
- 模拟快照 `locked-test-v1-2026-08-31`：全部九案及完整调查在 **2026-08-31 当日结束前已结案且可用**；
  五条 Query 的 `known_at = 2026-09-30`。
- **这是人为合成快照约定**，不是由 `detection_time` 推导的真实结案时间，也不表示已实现通用结案/可用时间过滤。
  发现日期检查只是必要条件，不代替结案/完整可用性依据。

## Case 摘要

| Case | 产品 / 路线 | 客户 | 异常 | 异常工序 | 发现阶段 / 日期 | 根因（来源候选） |
|---|---|---|---|---|---|---|
| LC001 | PROD_014 / LF_WB | CUS_002 | `00004` die tilt | P003 Die Attach | OQC / 2026-06-12 | 胶量或胶厚不均 |
| LC002 | PROD_007 / SUBSTRATE_WB | CUS_003 | `00004` die tilt | P003 Die Attach | OQC / 2026-06-14 | Die Attach位置/压力参数异常 |
| LC003 | PROD_008 / SUBSTRATE_WB | CUS_003 | `00004` + `00022` | P003 + P007 | In-process / 2026-06-25 | 胶量或胶厚不均 + Molding收缩与残余应力 |
| LC004 | PROD_008 / SUBSTRATE_WB | CUS_003 | `00022` warpage | P007 Molding | OQC / 2026-07-08 | Molding收缩与残余应力 |
| LC005 | PROD_007 / SUBSTRATE_WB | CUS_003 | `00022` warpage | P014 Material Income | Customer / 2026-06-20 | leadframe/substrate来料翘曲 |
| LC006 | PROD_012 / SUBSTRATE_FC | CUS_005 | `00030` bump open | P005 Flip Chip Attach | In-process / 2026-06-30 | flux/焊料量不足 |
| LC007 | PROD_016 / SUBSTRATE_FC | CUS_003 | `00030` bump open | P015 Wafer Income | OQC / 2026-07-15 | wafer来料bump高度/体积不一致或bump过低 |
| LC008 | PROD_017 / SUBSTRATE_FC | CUS_004 | `00031` bump short | P005 Flip Chip Attach | In-process / 2026-07-24 | 焊料量过多或reflow塌陷过度 |
| LC009 | PROD_010 / SUBSTRATE_FC | CUS_004 | `00031` bump short | P005 Flip Chip Attach | Customer / 2026-08-05 | FC placement偏移 |

LC003 的两种异常各有独立依据：LE105（几何量测）与 LE106（塑封条件）支持两条原因—证据—措施链；
LE107 为有观测依据的否定事实（同批 substrate 共面性抽检正常，排除来料翘曲）。

## Query 摘要

| Query | 产品 / 路线 | 客户 | 生产批 / 客户批 | 批号来源 | 已知异常 / 否定事实 |
|---|---|---|---|---|---|
| LQ001 | PROD_014 / LF_WB | CUS_002 | DEV_PL_109 / DEV_CL_109 | 新批 | 局部 die tilt（贴装面倾斜）；来料平整度与外观复查正常 |
| LQ002 | PROD_008 / SUBSTRATE_WB | CUS_003 | DEV_PL_110 / DEV_CL_110 | 新批 | 同一异常的不同表达（芯片与载体不平行、单边胶层偏厚）；已排除外观损伤 |
| LQ003 | PROD_007 / SUBSTRATE_WB | CUS_003 | DEV_PL_102 / DEV_CL_102 | **复用历史批** | 封装整体翘曲（碗形变形、焊球共面性超规格）；已排除运输搬运损伤 |
| LQ004 | PROD_012 / SUBSTRATE_FC | CUS_005 | DEV_PL_111 / DEV_CL_111 | 新批 | FC 互连开路（bump 未接合）；AOI 未发现异物污染 |
| LQ005 | PROD_017 / SUBSTRATE_FC | CUS_004 | DEV_PL_112 / DEV_CL_112 | 新批 | FC 互连短路（相邻 bump 焊料搭接） |

LQ001、LQ003、LQ004、LQ005 含当时已知的否定事实；Query 不含未来根因、改善措施或未知异常工序。

## 5 × 9 已确认标签矩阵

`1` = Relevant，`0` = Not Relevant。2026-10-08 用户确认，与草稿的差异见下方裁决记录。

| Case \ Query | LQ001 | LQ002 | LQ003 | LQ004 | LQ005 | 异常 |
|---|---|---|---|---|---|---|
| LC001 | 1 | 1 | 0 | 0 | 0 | die tilt |
| LC002 | 1 | 1 | **1** | 0 | 0 | die tilt |
| LC003 | 1 | 1 | 1 | 0 | 0 | die tilt + warpage |
| LC004 | 0 | **0** | 1 | 0 | 0 | warpage |
| LC005 | 0 | 0 | 1 | 0 | 0 | warpage |
| LC006 | 0 | 0 | 0 | 1 | 0 | bump open |
| LC007 | 0 | 0 | 0 | 1 | 0 | bump open |
| LC008 | 0 | 0 | 0 | 0 | 1 | bump short |
| LC009 | 0 | 0 | 0 | 0 | 1 | bump short |

正例数：LQ001=3、LQ002=3、LQ003=4、LQ004=2、LQ005=2，合计 **14 / 45**。

设计上的干扰与配对：同产品同族但异常不同（LQ002×LC004、LQ003×LC002）；
同族方向相反（LQ004×LC008、LQ005×LC006）；跨产品同异常（LQ001×LC002、LQ002×LC001 等）。

## 用户裁决记录（2026-10-08）

用户于 **2026-10-08** 确认全部 45 对标签、5 条 Query 的已知事实与合成快照依据，
正式 [qrels.json](qrels.json) 已发布（`human_confirmed`、`confirmed_on=2026-10-08`、
`confirmation_scope=locked_test_v1_corpus_and_all_45_binary_labels`）。
确认范围只覆盖 45 对标签与模拟可用性约定，**不自动升级源 Case 的语义审阅状态**。

与草稿的差异（2 对，草稿原为 `null`）：

| 配对 | 草稿 | 确认 | 依据 |
|---|---|---|---|
| `LQ002 × LC004` | `null` | **0** | 同为 PROD_008，但 LC004 只有 package warpage，与 LQ002 的 die tilt 异常不同；同产品背景不足以单独采用 |
| `LQ003 × LC002` | `null` | **1** | 同产品 PROD_007、**同生产批 DEV_PL_102**、同客户批；用户判定该背景足以采用，即使异常不同 |

**决策差异说明：** `LQ003 × LC002 = 1` 是用「同产品 + 同批次」背景单独定出的标签，
与 业务与评估约定 §2 现行文字「背景不单独决定相关性」不一致。按用户裁决保留并记录在
`qrels.json` 的 `label_policy` 与 `user_decisions`，**不改规则文字**；
其余 43 对按「异常相同才判 Relevant」的既有口径。

## 逐对理由入口

全部 45 对的确认标签、双侧事实理由与字段/ID 证据见 [qrels.json](qrels.json) 的 `judgments`；
裁决前后的逐对差异见该文件的 `user_decisions`，裁决前的建议与 `null` 项保留在 [qrels.draft.json](qrels.draft.json)。

## 已自动化覆盖 / 未自动化范围

- **已由确定性代码覆盖：** 版本与哈希绑定、ID 唯一、Query × Case 完整配对、确认状态与 split 守卫、
  批号固定属性（CR-08～10）、异常站点与产品路线并集（CR-49）、生成限制（GR-01/02/04/06）、
  来源记录与主数据候选一致、固定规模与复用批号自检。
- **未自动化：** 同义异常、易混淆对与弱相关边界依赖逐对人工判断；完整 Case / Evidence 语义审阅未完成。
  源 Case 的 `review_status` 保持 `draft_pending_human_review`，不因 qrels 确认而升级。
- 本目录只定义数据与审阅记录，不重复定义相关性规则；规则以 [业务与评估约定](../../../docs/design/behavior-contracts.md) 为准。

## 复现

```bash
uv run --locked python scripts/prepare_locked_test_v1.py --output-dir /tmp/locked-sandbox
```

脚本默认拒绝覆盖已有文件（`--force` 才覆盖），且永不写入正式 `qrels.json`。

## 冻结协议与历史引用

`protocol.md` 作为预登记的冻结材料逐字节保留；其中 Current Plan 与 M6-03 任务包的三个链接属于当时的本地过程引用，公开源码树不提供这些过程文件，它们不参与运行。现行定义见[业务与评估约定](../../../docs/design/behavior-contracts.md)，冻结后的实际单次运行范围和裁决差异见本页及[结果说明](../../../results/locked-test-v1/README.md)。

协议原始 SHA-256：`ac54a31e06ccb07faab5debd109a403b7a03bd025fded391ea9e8d1f398d912f`。协议记录的源码、生成脚本和数据身份为冻结时身份；本次目录分离没有重评 Locked Test，也没有刷新原始哈希。
