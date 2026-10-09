# dev-v3 Grounded Answer 最终评估（v10）

2026-10-03 的五条真实回答与逐项语义审阅，按学习展示范围接受。当前页面汇总既有观测；此次目录分离没有调用模型或重评质量。

## 输入与方法

- dev-v3：9 个历史 Case、5 条 Query；快照 `dev-v3-2026-09-15`，R3 检索，`top_k=4`。
- DeepSeek `deepseek-flash`，非思考、JSON Output、temperature=0、max_tokens=4096，SDK 自动重试关闭；提示词 `grounded_answer_v10`。
- 完整输入、排名、上下文、实际发送消息、响应和运行身份见 [v10 原始记录](m4/dev-v3-answer-v10/)；qrels 只用于评估，不进入检索或生成。
- [现行业务规则](../docs/design/behavior-contracts.md)依据异常调查参考价值采用案例；相同产品、批次或产品族只作背景补充，不强制采用。

## 五条保存的真实回答

| Query | 状态 | 模型耗时 | tokens | 引用检查 / 问题 | 采用 | 跳过 |
|---|---|---:|---:|---:|---|---|
| Q001 | ok | 6.49s | 6164 | 25 / 0 | C001 C003 C007 | C004 |
| Q002 | ok | 5.37s | 5626 | 18 / 0 | C005 C008 | C002 C006 |
| Q003 | ok | 3.95s | 5158 | 11 / 0 | C006 | C009 C005 C008 |
| Q004 | ok | 5.46s | 5657 | 18 / 0 | C008 C005 | C002 C003 |
| Q005 | ok | 7.33s | 6367 | 25 / 0 | C007 C001 C003 | C004 |

合计 28972 tokens、97 项引用检查，均无定位问题。耗时为单次读数，不支持效率结论；`ok` 表示格式和引用守卫通过，不表示所有语义正确。

## 语义结论与失败边界

[完整语义审阅](m4/dev-v3-answer-v10/semantic-review.json)共 145 单元：143 supported、1 unsupported、1 uncertain。审阅单位为字段或数组项，不是原子事实准确率，也不是用户确认的新 Ground Truth。历史原因、改善措施、检查结果各 11/11 与同 Case 原文一致；当前根因断言为 0。

- **Q005×C007 relevance_reason：unsupported。** “双方在…分离面位置上均有可对照的已知事实”过强，Query 只给调查重点在键合界面；采用本身有焊盘脱开参考依据。此措辞限制在学习展示范围接受。
- **Q003 current_gaps[1]：uncertain。** “对托盘或运输防护接触痕迹的检查结果”可能指进一步检查，也可能覆盖已有托盘碰伤观察；保留这一歧义。

旧版报告中的“unsupported=0”“全部边界通过”结论已撤回，因审阅范围不完整，不能继续用于描述最终质量。旧原始成功/失败记录与完整修复过程保存在本地；这里保留最终结论和必要回归夹具。

Development r2 qrels 仍是旧相关性口径，`human_confirmed` 不等于新口径确认。Q001×C002、Q001×C004、Q003×C005 的旧理由依赖背景充分条件，未自动重标；Q005×C004 的既有弱相关裁决也未被推翻。Recall@4=0.96 仅代表旧检索实验，不构成新规则质量结论。

## 回放与复现

无需模型调用的检查：

```bash
uv run --locked casetrace answer --query-id Q005 --check-only
uv run --locked python scripts/m4_04_run_all.py --check-only
```

保存回答的真实数据库/API 回放与浏览器检查见 [Web Demo 离线验收](../docs/development/web-demo.md#离线验收不调用模型不计费)。需要另做真实模型运行时，先配置凭据，再显式使用新目录：

```bash
uv run --locked python scripts/m4_04_run_all.py --output-dir /tmp/casetrace-answer-next-run
```

批处理在调用模型前检查所有目标文件，拒绝覆盖已有证据；失败记录也保留。模型别名不是不可变版本，不承诺逐字复现。

## 历史身份

原始 v10 记录及其历史哈希保持原样。此次将批处理脚本从 `tmp/` 提升到 `scripts/`，并调整注释和身份采集路径，新运行的源码身份会变化；不能宣称历史指纹对应整理后的源码。目录分离不改变数据、标签、提示词或业务行为。
