# Locked Test 单次链路验证（2026-10-08）

**这不是多方法对比，也不产生选型结论。** 按用户 2026-10-08 的范围精简决定：只运行已选固定方案 **R3**
（`bm25_drop_negation_labels`）一次，确认评估链路（加载 → 版本/split/快照校验 → 检索 → 计分 → 报告）可运行。
结果好坏均接受，不追加调参、不扩充数据、不反复评审。协议与冻结身份见
[protocol.md](../../data/evaluation/locked-test-v1/protocol.md)，标签来源见
[locked-test-v1 说明](../../data/evaluation/locked-test-v1/README.md)。

## 运行

```bash
uv run --locked casetrace evaluate \
  --qrels data/evaluation/locked-test-v1/qrels.json \
  --method bm25_drop_negation_labels \
  --output results/locked-test-v1/r3.json
```

| 项 | 值 |
|---|---|
| 结果 | [r3.json](r3.json)；终端附件 [r3.cli.txt](r3.cli.txt)；exit 0 |
| 输入身份 | qrels `d6ad943390f9b713…`、语料 `2fdc390ac65eb023…`、主数据 `f5001bddd3dff433…` |
| split / 快照 | `locked_test` / `locked-test-v1-2026-08-31`（完整可用日 2026-08-31） |
| 方法 | 报告记 `bm25_filtered_query_terms`（= R3，H1+H2 Query 侧过滤）；`rank_bm25.BM25Okapi`，k1=1.5 / b=0.75 / epsilon=0.25 |
| 语料范围 | 9 Case；LQ001～LQ005 实际返回 9 / 7 / 9 / 8 / 9 条，保留实际返回，不补名次 |
| 运行时间 | `generated_at = 2026-10-08T15:12:26+00:00`；索引 0.0015 s、总耗时 0.0139 s（单次读数，不支持效率结论） |

## 汇总指标（5 条 Query 全部参与）

| 指标 | @1 | @3 | @4 |
|---|---|---|---|
| Recall | 0.3833 | 0.7833 | **0.8833** |
| Precision | 1.0000 | 0.7333 | 0.6000 |
| nDCG | 1.0000 | 0.8757 | 0.8949 |

MRR@4 = **1.0000**（每条 Query 前四条都至少命中一个正例）。

汇总为 5 条 Query 的**等权平均**（先算逐 Query 分数，再对参与 Query 求平均），
不是把所有正例合并成一个池计算；MRR=1 只表示各 Query 首条命中，**不表示没有漏检**。

## 逐 Query

| Query | 正例数 | 前四条 | 前四命中 | 漏掉（名次） |
|---|---|---|---|---|
| LQ001 | 3 | LC001 > LC003 > LC004 > LC005 | 2 / 3 | LC002（5） |
| LQ002 | 3 | LC002 > LC003 > LC001 > LC006 | 3 / 3 | — |
| LQ003 | 4 | LC005 > LC004 > LC003 > LC009 | 3 / 4 | LC002（9） |
| LQ004 | 2 | LC006 > LC008 > LC009 > LC007 | 2 / 2 | — |
| LQ005 | 2 | LC009 > LC008 > LC006 > LC007 | 2 / 2 | — |

## 观察与限制

- 链路本身运行正常：输入校验、快照依据、逐 Query 排名、指标与可复现字段都完整写出，无异常或空命中。
- 主要漏检是 `(LQ003, LC002)`：该对是用户判为 Relevant 的同产品**同批次**、异常不同（die tilt vs 翘曲）的配对，
  在 R3 下排到第 9（末位，本次运行只命中 1 个通用词）。这是**用户逐对裁决**的结果：以同产品 + 同生产批 +
  同客户批背景采用，与 [业务与评估约定](../../docs/design/behavior-contracts.md) 通用规则“背景不单独决定相关性”
  **存在差异**；按裁决保留、不作全局标签规则，详见
  [数据版本说明的裁决记录](../../data/evaluation/locked-test-v1/README.md#用户裁决记录2026-10-08)。
  **本记录不据此调整标签或方法**。
- `(LQ001, LC002)` 排第 5，属同异常的跨产品参考，同样超出 K=4。
- 9 Case / 5 Query 是小样本；快照是人为合成约定；单次运行不构成质量或效率结论。
- 不与 Development 数值直接比较或计算提升（口径与规模不同）。

## 明确不做（按用户决定）

不做五方法对比、不做计时重复、不做错误分析调参、不扩充数据、不重新评审标签；
完整多方法对比属于后续另行确认的实验范围。
