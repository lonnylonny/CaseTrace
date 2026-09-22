# CaseTrace

本词汇表用于区分历史质量案例的调查参考价值与当前异常的原因结论。具体相关性规则和评估约定见 [Current Plan](docs/project/current-plan.md#4-retrieval--ground-truth--evaluation-约定)。

## Language

**Relevant（检索相关）**：
针对当前异常当时已知的信息，值得工程师查看的历史 Case。该判断表示调查参考价值，不表示当前与历史原因相同，也不表达相关 Case 之间的阅读优先级。
_Avoid_：当前根因已命中、同根因案例

**Similar Product（类似产品）**：
本轮指与当前已知产品属于同一 Product Family 的产品。仅采用相同 Package Route 不足以称为类似产品。
_Avoid_：同封装路线产品（作为类似产品的同义词）

**Closed Historical Case（已结案历史案例）**：
在当前异常查询时点之前已经结案，且结案内容已可供查看的历史调查记录。仅已发现异常的记录不等于已结案历史案例。

**Abnormal Process（异常站点）**：
调查确认涉及异常的工序。一个案例可以涉及多个异常站点；原因未确认不等于站点未确认。
_Avoid_：检出阶段、候选发生工序（作为已确认异常站点的同义词）

**Detection Stage（发现阶段）**：
异常被发现或反馈时所处的阶段，例如 OQC 或 Customer；它不直接说明异常发生于哪个工序。

**Same Abnormal Process（同站点异常关联）**：
一组历史案例共同涉及至少一个已确认的异常站点，不要求异常表现或根因相同。这种联系不等于异常复发，也不单独决定检索相关性。
