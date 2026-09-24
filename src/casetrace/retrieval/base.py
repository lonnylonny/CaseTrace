"""检索方法的公共契约：评估器只依赖这里声明的最小接口。

评估器需要一种方法按 Case ID 接收历史检索文本、按 Query 文本检索，
并返回语料内有效且唯一的 Case ID 与分数；相关性标签只参与计分，不进入检索。
命中词项是可选的：语义检索没有词项信息时用 None 表示，不伪造空列表。
具体实现（BM25、后续的 Embedding 等）由评估入口按方法名选择。
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    """一次检索命中的一条 Case；名次由返回顺序决定，不在这里保存。"""

    case_id: str
    score: float
    # None 表示该方法不提供命中词项信息，与"命中但词项为空"区分开。
    matched_terms: list[str] | None = None


class Retriever(Protocol):
    """检索方法必须提供的行为；建索引在构造时完成，检索只接收 Query 文本。"""

    def search(self, query: str, *, top_k: int) -> list[SearchHit]:
        """返回按方法自身相关度降序排列的命中；分数不是相关概率。"""
        ...

    def describe(self) -> dict:
        """该方法自己的元数据（实现、分词或编码、参数），供报告如实记录。"""
        ...

    # 可选能力：实现可以提供 run_details() -> dict，返回本次运行的观测值
    # （例如耗时、缓存命中状态）。评估器只在存在时把它记入报告的顶层 timing.method_details，
    # 因此这些值不会混进可比较的排名、分数与方法配置。

