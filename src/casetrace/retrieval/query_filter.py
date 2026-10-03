"""M3-06 针对性实验：BM25 的 Query 侧词项过滤（语料、索引与历史文本都不变）。

依据是 dev-v3 已验收结果的错误：Q005 的排名被 Query 自身写明的“排除”概念
（碰伤 / 运输）与标识段标签词（客户 / 产品 / 涉及）抬高。这里只提供两条可单独
开启的过滤规则，供单变量对照使用；它不是生产检索方案，是否采纳由 M3-07 按证据决定。

- H1 `drop_negation_clauses`：含否定线索的小句整句不参与计分；
- H2 `drop_label_terms`：主数据 ID 与引出 ID 的模板标签词不参与计分。

过滤只作用于 Query 词项，历史 Case 文本与索引不变；命中词项仍由实际参与的 Query
词项决定，因此报告里的 `matched_terms` 能反映本次过滤。
"""

import re

from casetrace.retrieval.bm25 import BM25Retriever, tokenize

# 小句分隔：中文与英文标点都切开，便于按小句判断否定语义。
CLAUSE_SEPARATOR_PATTERN = re.compile(r"[，。；：！？,.;:!?]+")

# 否定线索：小句只要含任一标记，整句词项都不参与计分（例如“已排除…的可能”“…尚未确认”）。
NEGATION_MARKERS = ("排除", "不", "未", "无", "非")

# 标识标签词：Query 模板里引出主数据 ID 的固定说法，按双字切分后的形态列出。
LABEL_TOKENS = frozenset({"涉及", "及客", "客户", "生产", "产批", "户批", "产品"})

# 主数据 ID：产品、客户，以及生产批 / 客户批使用的 DEV_ 编号。
ID_PATTERN = re.compile(r"(?:prod|cus|dev)_[a-z0-9_]+")


def split_clauses(query: str) -> list[str]:
    """按中英文标点切分小句，去掉空白与空小句。"""
    return [clause.strip() for clause in CLAUSE_SEPARATOR_PATTERN.split(query) if clause.strip()]


def strip_negation_clauses(query: str) -> str:
    """去掉含否定线索的小句，其余小句按原顺序拼回。"""
    kept = [
        clause for clause in split_clauses(query)
        if not any(marker in clause for marker in NEGATION_MARKERS)
    ]
    return "，".join(kept)


def is_label_token(token: str) -> bool:
    """词项是否属于标识段：主数据 ID，或引出 ID 的模板标签词。"""
    return bool(ID_PATTERN.fullmatch(token)) or token in LABEL_TOKENS


def filtered_query_tokens(
    query: str, *, drop_negation_clauses: bool = False, drop_label_terms: bool = False,
) -> list[str]:
    """按启用的规则返回参与计分的 Query 词项；两项都关闭时等价于 `tokenize(query)`。"""
    text = strip_negation_clauses(query) if drop_negation_clauses else query
    tokens = tokenize(text)
    if drop_label_terms:
        tokens = [token for token in tokens if not is_label_token(token)]
    return tokens


class FilteredBM25Retriever(BM25Retriever):
    """同一 BM25 索引，只在 Query 侧过滤词项的对照变体（M3-06 实验用）。"""

    def __init__(self, documents, *, drop_negation_clauses=False, drop_label_terms=False):
        super().__init__(documents)
        if not (drop_negation_clauses or drop_label_terms):
            raise ValueError("过滤变体至少要启用一条规则；不需要过滤时请使用 bm25")
        self.drop_negation_clauses = bool(drop_negation_clauses)
        self.drop_label_terms = bool(drop_label_terms)

    def query_tokens(self, query: str) -> list[str]:
        return filtered_query_tokens(
            query,
            drop_negation_clauses=self.drop_negation_clauses,
            drop_label_terms=self.drop_label_terms,
        )

    def describe(self) -> dict:
        description = super().describe()
        description["method"] = "bm25_filtered_query_terms"
        description.update({
            "query_filter": {
                "drop_negation_clauses": self.drop_negation_clauses,
                "drop_label_terms": self.drop_label_terms,
                "negation_markers": list(NEGATION_MARKERS),
                "label_tokens": sorted(LABEL_TOKENS),
                "id_pattern": ID_PATTERN.pattern,
            },
            "note": (
                "M3-06 针对性实验变体：索引与历史文本与 bm25 相同，只过滤 Query 词项；"
                "不是生产检索方案，是否采纳由 M3-07 按证据决定。分数不是相关概率。"
            ),
        })
        return description
