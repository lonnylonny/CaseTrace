"""本地 BM25 基线：文档和查询使用同一切词规则，结果始终保留来源 Case ID。"""

import re
import unicodedata

from rank_bm25 import BM25Okapi

from casetrace.retrieval.base import SearchHit

# SearchHit 的定义在公共契约模块 base 中；这里继续导出，调用方的导入路径不变。


def tokenize(text: str) -> list[str]:
    """中文按相邻双字切分；英文和带连字符／下划线的 ID 保持完整。

    这是不依赖词典的初始基线，例如“焊线脱落”得到“焊线、线脱、脱落”。
    它不理解同义词；后续根据开发数据的检索误差决定是否更换分词器。
    """
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = []
    for part in re.findall(r"[a-z0-9]+(?:[_-][a-z0-9]+)*|[\u4e00-\u9fff]+", text):
        if "\u4e00" <= part[0] <= "\u9fff" and len(part) > 1:
            tokens.extend(part[index:index + 2] for index in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


class BM25Retriever:
    """输入为 case_id → 历史检索文本；不接收或使用相关性标签。"""

    def __init__(self, documents: dict[str, str]):
        if not documents:
            raise ValueError("检索语料不能为空")
        self.case_ids = sorted(documents)
        corpus = [tokenize(documents[case_id]) for case_id in self.case_ids]
        if any(not tokens for tokens in corpus):
            raise ValueError("每条历史案例必须有可检索的文本")
        self.term_sets = [set(tokens) for tokens in corpus]
        self.index = BM25Okapi(corpus)

    def describe(self) -> dict:
        """报告用的方法元数据；参数取实际索引实例，不在这里另抄一份常量。"""
        return {
            "method": "bm25_okapi",
            "implementation": "rank_bm25.BM25Okapi",
            "tokenizer": "casetrace.retrieval.bm25.tokenize",
            "parameters": {
                "k1": float(self.index.k1), "b": float(self.index.b),
                "epsilon": float(self.index.epsilon),
            },
            "note": "保留 BM25 实际返回的全部条目，不补分数、不补名次；分数不是相关概率。",
        }

    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k 必须是正整数")
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.index.get_scores(tokens)
        query_terms = set(tokens)
        hits = []
        for case_id, score, terms in zip(self.case_ids, scores, self.term_sets):
            matched_terms = sorted(query_terms & terms)
            # Okapi 在小语料中可能给出零或负分；完全无词项重合时才视为未命中。
            if matched_terms:
                hits.append(SearchHit(case_id, float(score), matched_terms))
        return sorted(hits, key=lambda hit: (-hit.score, hit.case_id))[:top_k]
