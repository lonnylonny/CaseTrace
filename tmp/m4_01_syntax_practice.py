"""语法练习：三个模式，用玩具数据跑，和项目无关。

跑：uv run python tmp/m4_01_syntax_practice.py
"""

# 玩具数据：三条记录，其中两条 case_id 相同，模拟"一个 Case 有多条 Detail"。
rows = [
    {"case_id": "A", "text": "第一条"},
    {"case_id": "B", "text": "第二条"},
    {"case_id": "A", "text": "第三条"},
]

# ---- 模式 1：建"编号 → 记录"的字典（适合一对一，比如 Case）----
# 读法：对 rows 里每一条 row，取 row["case_id"] 当键、row 当值
by_id = {row["case_id"]: row for row in rows}
print("模式 1  by_id =", by_id)
print("         by_id['B'] =", by_id["B"])
print("         'C' in by_id →", "C" in by_id)          # 用字典判断"在不在"才对
print("         'A' in rows →", "A" in rows)            # 用原列表判断是错的：列表里装的是字典，不是编号

# ---- 模式 2：筛出"全部符合条件的"（适合一对多，比如 Detail / Evidence）----
# 读法：把 rows 里每一条 row 留下来，条件是 row["case_id"] 等于 "A"
same_a = [row for row in rows if row["case_id"] == "A"]
print("模式 2  same_a =", same_a)
print("         条数 =", len(same_a))                   # 两条都保住了，不会被覆盖

# ---- 模式 3：先建空列表，边循环边往里放，最后整体返回 ----
collected = []
for index, row in enumerate(rows, start=1):
    collected.append((index, row["case_id"]))
print("模式 3  collected =", collected)                # 每圈都追加，最后拿到全部

# ---- 对照：花括号里用逗号分开是"集合"，不是字典 ----
print("集合      {1, 2, 3} →", {1, 2, 3})
# 集合不能装列表：下面这行会报 TypeError: unhashable type: 'list'
# print({rows})
