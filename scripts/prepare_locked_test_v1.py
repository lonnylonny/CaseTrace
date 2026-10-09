"""生成 locked-test-v1 的语料与 qrels 草稿（M6-03 SD2）。

按 GR-10：先由 Python 确定客户/产品、Detail、批号、时间、Failure Mode、数量、
Case.abnormal_processes 及其调查依据、Evidence 类型与 relevance、原因/措施候选，
以及证据里的实际 equipment_id；文本字段只描述这些已确定的事实。
脚本不调用任何模型服务，也不引入生成平台。

守卫：
* 生成步骤只写 `data/locked-test/corpus-v1.json` 与
  `data/evaluation/locked-test-v1/qrels.draft.json`；
* 正式 `qrels.json` 只在用户确认后由 `--publish-qrels --confirmed-on` 显式发布；
* 目标文件已存在时拒绝覆盖，`--force` 才覆盖；
* 先在临时文件上用既有加载器校验，校验失败不落盘。

用法：
    uv run --locked python scripts/prepare_locked_test_v1.py
    uv run --locked python scripts/prepare_locked_test_v1.py --output-dir /tmp/locked-sandbox
    uv run --locked python scripts/prepare_locked_test_v1.py --force
    uv run --locked python scripts/prepare_locked_test_v1.py --publish-qrels --confirmed-on 2026-10-08
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
import random
import tempfile
from pathlib import Path

from casetrace.data.reference import ReferenceData, load_reference
from casetrace.demo import check_source_records, load_validated_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_RELATIVE = "data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx"
CORPUS_RELATIVE = "data/locked-test/corpus-v1.json"
QRELS_DRAFT_RELATIVE = "data/evaluation/locked-test-v1/qrels.draft.json"
# 正式 qrels：只在用户确认后由 `--publish-qrels` 显式发布，生成路径永不写它。
QRELS_RELATIVE = "data/evaluation/locked-test-v1/qrels.json"

CORPUS_VERSION = "locked-test-corpus-v1"
QRELS_VERSION = "locked-test-qrels-v1"
SPLIT = "locked_test"
REVIEW_STATUS = "draft_pending_human_review"

# 固定种子：用于从主数据候选中确定 equipment_id；不改动任何文本或标签。
SEED = 20260831

SNAPSHOT_ID = "locked-test-v1-2026-08-31"
COMPLETE_AVAILABLE_ON = "2026-08-31"
QUERY_KNOWN_AT = "2026-09-30"
SNAPSHOT_BASIS = (
    "人为合成快照约定：全部九条 Locked Test Case 及其完整调查被设定为在 2026-08-31 当日结束前"
    "已结案且可供查看，全部 Detail 的 detection_time 均不晚于该日。它验证的是用户确认的合成约定，"
    "不是由 detection_time 推导的真实结案时间，也不表示已实现通用结案/可用时间过滤。"
)

# 事实表：产品/批号/时间/数量/异常/工序/原因措施候选都是确定值；文本只描述这些事实。
# `equipment_process` 存在时由脚本按 SEED 从主数据的该工序设备中确定 equipment_id。
CASES = (
    {
        "case_id": "LC001",
        "product_id": "PROD_014",
        "abnormal_types": ("00004",),
        "abnormal_processes": ("P003",),
        "abnormal_description": "OQC X-ray 与剖面检查发现芯片贴装面倾斜，芯片对角位置胶层厚度差超出规格，"
                                "器件内部芯片一端高于另一端，表现为 die tilt；异常位于 Die Attach 形成的贴装界面。",
        "root_cause": "结案确认：Die Attach 胶量或胶厚不均，导致芯片贴装面倾斜。",
        "corrective_action": "控制胶量、胶厚和adhesive状态，并优化贴装位置与压力。",
        "detail": {
            "detail_id": "LD001", "production_lot": "DEV_PL_101", "customer_lot": "DEV_CL_101",
            "production_time": "2026-06-05", "detection_stage": "OQC", "detection_time": "2026-06-12",
            "affected_qty": 320, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE101", "checkpoint_type": "Production", "custom_name": None,
                "result": "Die Attach 设备 {equipment} 记录显示异常批点胶量在异常时段内波动超出控制范围，"
                          "贴装压力参数与标准值偏离；上芯台与吸嘴复查未发现异物。",
                "relevance": "related", "equipment_process": "P003",
            },
            {
                "checkpoint_id": "LE102", "checkpoint_type": "QC", "custom_name": None,
                "result": "X-ray 剖面复查确认倾斜方向与点胶偏厚一侧一致；同批 leadframe 来料平整度抽检正常，"
                          "未发现载体变形。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00004", "root_cause": "胶量或胶厚不均",
            "corrective_action": "控制胶量、胶厚和adhesive状态",
            "family": "geometry-tilt-warpage", "synonym_of": None,
            "coverage": "局部 die tilt 的基准案例；同类异常的措辞父项",
        },
    },
    {
        "case_id": "LC002",
        "product_id": "PROD_007",
        "abnormal_types": ("00004",),
        "abnormal_processes": ("P003",),
        "abnormal_description": "OQC 声学扫描显示芯片贴装面与载体基准面不平行，一侧胶层偏薄、对角偏厚，"
                                "扫描影像呈单边倾斜的 die tilt 特征；异常位于 Die Attach 贴装界面。",
        "root_cause": "结案确认：Die Attach位置/压力参数异常，使芯片贴装面倾斜。",
        "corrective_action": "优化贴装位置与压力，并稳定 Die Attach 过程。",
        "detail": {
            "detail_id": "LD002", "production_lot": "DEV_PL_102", "customer_lot": "DEV_CL_102",
            "production_time": "2026-06-10", "detection_stage": "OQC", "detection_time": "2026-06-14",
            "affected_qty": 420, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE103", "checkpoint_type": "Production", "custom_name": None,
                "result": "Die Attach 设备 {equipment} 的贴装位置与压力记录在异常时段偏离控制范围，"
                          "位置偏移方向与倾斜方向一致。",
                "relevance": "related", "equipment_process": "P003",
            },
            {
                "checkpoint_id": "LE104", "checkpoint_type": "Material", "custom_name": None,
                "result": "同批 die attach adhesive MAT_007 的来料粘度与到货检验记录一致，"
                          "未发现 adhesive 状态异常。",
                "relevance": "not_related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00004", "root_cause": "Die Attach位置/压力参数异常",
            "corrective_action": "优化贴装位置与压力",
            "family": "geometry-tilt-warpage", "synonym_of": "LC001",
            "coverage": "相同异常的不同表达（基板路线、声学扫描措辞）",
        },
    },
    {
        "case_id": "LC003",
        "product_id": "PROD_008",
        "abnormal_types": ("00004", "00022"),
        "abnormal_processes": ("P003", "P007"),
        "abnormal_description": "In-process 声学扫描同时发现两类几何异常：芯片贴装面明显倾斜，表现为 die tilt；"
                                "同一器件的封装整体呈弓形翘曲，边缘与中心存在高度差，表现为 package warpage；"
                                "两者分别位于 Die Attach 贴装界面与塑封后的封装本体。",
        "root_cause": "结案确认：Die Attach 胶量或胶厚不均造成 die tilt，塑封 Molding收缩与残余应力叠加造成 package warpage。",
        "corrective_action": "控制胶量、胶厚和adhesive状态，并优化Molding/PMC。",
        "detail": {
            "detail_id": "LD003", "production_lot": "DEV_PL_103", "customer_lot": "DEV_CL_103",
            "production_time": "2026-06-18", "detection_stage": "In-process", "detection_time": "2026-06-25",
            "affected_qty": 540, "disposition": "本事件纳入处置范围的产品全部隔离，经复查后报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE105", "checkpoint_type": "QC", "custom_name": None,
                "result": "声学扫描与 X-ray 剖面确认芯片贴装面倾斜及对角胶层厚度差，"
                          "同时测出封装整体弓形翘曲量超出规格。",
                "relevance": "related", "equipment_process": None,
            },
            {
                "checkpoint_id": "LE106", "checkpoint_type": "Production", "custom_name": None,
                "result": "塑封设备 {equipment} 与后固化记录显示模温与后固化曲线在异常时段偏离设定，"
                          "收缩条件与翘曲量测结果对应。",
                "relevance": "related", "equipment_process": "P007",
            },
            {
                "checkpoint_id": "LE107", "checkpoint_type": "QC", "custom_name": None,
                "result": "同批 substrate MAT_003 来料共面性抽检正常，未发现载体来料翘曲，"
                          "排除来料翘曲作为本次翘曲主因。",
                "relevance": "not_related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00004", "root_cause": "胶量或胶厚不均",
            "corrective_action": "控制胶量、胶厚和adhesive状态",
            "family": "geometry-tilt-warpage", "synonym_of": None,
            "coverage": "双异常：die tilt 与 package warpage 各有独立依据",
            "additional_failure_modes": (
                {"failure_mode_id": "00022", "root_cause": "Molding收缩与残余应力",
                 "corrective_action": "优化Molding/PMC"},
            ),
        },
    },
    {
        "case_id": "LC004",
        "product_id": "PROD_008",
        "abnormal_types": ("00022",),
        "abnormal_processes": ("P007",),
        "abnormal_description": "OQC 平面度测量发现封装整体呈弓形翘曲，四角与中心高度差异超出规格，"
                                "塑封体表面不平整，表现为 package warpage；异常位于塑封后的封装本体。",
        "root_cause": "结案确认：Molding收缩与残余应力导致封装整体翘曲。",
        "corrective_action": "优化Molding/PMC，并匹配材料CTE。",
        "detail": {
            "detail_id": "LD004", "production_lot": "DEV_PL_104", "customer_lot": "DEV_CL_104",
            "production_time": "2026-07-01", "detection_stage": "OQC", "detection_time": "2026-07-08",
            "affected_qty": 260, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE108", "checkpoint_type": "Production", "custom_name": None,
                "result": "塑封设备 {equipment} 的模温与保压记录在异常时段超出控制范围，"
                          "调整后对照批翘曲量回到规格内。",
                "relevance": "related", "equipment_process": "P007",
            },
            {
                "checkpoint_id": "LE109", "checkpoint_type": "QC", "custom_name": None,
                "result": "平面度测量复现弓形翘曲；X-ray 剖面未发现芯片贴装面倾斜，"
                          "排除局部 die tilt 作为主因。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00022", "root_cause": "Molding收缩与残余应力",
            "corrective_action": "优化Molding/PMC",
            "family": "geometry-tilt-warpage", "synonym_of": None,
            "coverage": "封装整体翘曲的塑封路线依据；与局部 die tilt 区分",
        },
    },
    {
        "case_id": "LC005",
        "product_id": "PROD_007",
        "abnormal_types": ("00022",),
        "abnormal_processes": ("P014",),
        "abnormal_description": "客户来料复查时测出封装整体翘曲，器件在常温下呈碗形变形，焊球共面性超出规格，"
                                "表现为 package warpage；异常与载体来料的几何状态相关。",
        "root_cause": "结案确认：leadframe/substrate来料翘曲导致封装整体翘曲。",
        "corrective_action": "控制载体来料平整度，并稳定 Die Attach 过程。",
        "detail": {
            "detail_id": "LD005", "production_lot": "DEV_PL_102", "customer_lot": "DEV_CL_102",
            "production_time": "2026-06-10", "detection_stage": "Customer", "detection_time": "2026-06-20",
            "affected_qty": 180, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE110", "checkpoint_type": "Material", "custom_name": None,
                "result": "该批 substrate MAT_004 的来料共面性复测超出规格，翘曲方向与成品翘曲一致，"
                          "来料批号与供货记录可追溯。",
                "relevance": "related", "equipment_process": None,
            },
            {
                "checkpoint_id": "LE111", "checkpoint_type": "QC", "custom_name": None,
                "result": "塑封设备与后固化记录正常，模温与固化曲线均在设定范围内，"
                          "排除塑封条件作为本次翘曲主因。",
                "relevance": "not_related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00022", "root_cause": "leadframe/substrate来料翘曲",
            "corrective_action": "控制载体来料平整度",
            "family": "geometry-tilt-warpage", "synonym_of": None,
            "coverage": "整体翘曲的来料载体依据；与同批 die tilt 案例共用生产批但异常不同",
        },
    },
    {
        "case_id": "LC006",
        "product_id": "PROD_012",
        "abnormal_types": ("00030",),
        "abnormal_processes": ("P005",),
        "abnormal_description": "In-process 电性测试发现部分 FC 器件互连开路，X-ray 显示个别 bump 与 substrate pad "
                                "之间未形成有效接合，表现为 bump open；异常位于 Flip Chip Attach 接合界面。",
        "root_cause": "结案确认：flux/焊料量不足，造成 bump 与 pad 未有效接合。",
        "corrective_action": "优化FC placement、flux和reflow，并保证接合共面性。",
        "detail": {
            "detail_id": "LD006", "production_lot": "DEV_PL_105", "customer_lot": "DEV_CL_105",
            "production_time": "2026-06-22", "detection_stage": "In-process", "detection_time": "2026-06-30",
            "affected_qty": 700, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE112", "checkpoint_type": "Production", "custom_name": None,
                "result": "Flip Chip Attach 设备 {equipment} 的 flux 喷涂量与 reflow 温度曲线记录显示"
                          "异常批用量偏低、峰值温度不足。",
                "relevance": "related", "equipment_process": "P005",
            },
            {
                "checkpoint_id": "LE113", "checkpoint_type": "QC", "custom_name": None,
                "result": "X-ray 复查确认未接合 bump 的位置与 flux 覆盖不足的区域一致，同批其它区域接合正常。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00030", "root_cause": "flux/焊料量不足",
            "corrective_action": "优化FC placement、flux和reflow",
            "family": "fc-bump-open-short", "synonym_of": None,
            "coverage": "FC 互连开路（助焊剂/焊料量）；与 bump short 形成易混淆对照",
        },
    },
    {
        "case_id": "LC007",
        "product_id": "PROD_016",
        "abnormal_types": ("00030",),
        "abnormal_processes": ("P015",),
        "abnormal_description": "OQC X-ray 检查发现 FC 器件存在 bump 未接合的开路现象，未接合位置集中在 bump 高度偏低的"
                                "区域，表现为 bump open；异常位于 Flip Chip Attach 形成的互连界面。",
        "root_cause": "结案确认：wafer来料bump高度/体积不一致或bump过低，造成接合开路。",
        "corrective_action": "控制wafer bump一致性，并优化FC placement、flux和reflow。",
        "detail": {
            "detail_id": "LD007", "production_lot": "DEV_PL_106", "customer_lot": "DEV_CL_106",
            "production_time": "2026-07-05", "detection_stage": "OQC", "detection_time": "2026-07-15",
            "affected_qty": 450, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE114", "checkpoint_type": "Material", "custom_name": None,
                "result": "该片 wafer 来料 bump 高度数据分布偏低，超出规格下限的 bump 与未接合位置一致；"
                          "wafer 批号与来料记录可追溯。",
                "relevance": "related", "equipment_process": None,
            },
            {
                "checkpoint_id": "LE115", "checkpoint_type": "AOI", "custom_name": None,
                "result": "AOI 记录显示该批 bump 高度分布整体偏低，与来料 wafer 测量方向一致。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00030", "root_cause": "wafer来料bump高度/体积不一致或bump过低",
            "corrective_action": "控制wafer bump一致性",
            "family": "fc-bump-open-short", "synonym_of": None,
            "coverage": "FC 开路的 wafer 来料依据（跨工序，P015）",
        },
    },
    {
        "case_id": "LC008",
        "product_id": "PROD_017",
        "abnormal_types": ("00031",),
        "abnormal_processes": ("P005",),
        "abnormal_description": "In-process 电性测试发现相邻 bump 之间出现桥连接通，X-ray 显示局部焊料外溢并连成整体，"
                                "表现为 bump short；异常位于 Flip Chip Attach 接合界面。",
        "root_cause": "结案确认：焊料量过多或reflow塌陷过度，造成相邻 bump 桥连。",
        "corrective_action": "控制焊料量，并优化FC placement和reflow。",
        "detail": {
            "detail_id": "LD008", "production_lot": "DEV_PL_107", "customer_lot": "DEV_CL_107",
            "production_time": "2026-07-12", "detection_stage": "In-process", "detection_time": "2026-07-24",
            "affected_qty": 380, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE116", "checkpoint_type": "Production", "custom_name": None,
                "result": "Flip Chip Attach 设备 {equipment} 的 reflow 峰值温度与焊料量记录在异常时段偏高，"
                          "桥连位置集中在同一区域。",
                "relevance": "related", "equipment_process": "P005",
            },
            {
                "checkpoint_id": "LE117", "checkpoint_type": "QC", "custom_name": None,
                "result": "X-ray 切片确认相邻 bump 之间焊料连通，接合界面完整，排除开路类异常。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00031", "root_cause": "焊料量过多或reflow塌陷过度",
            "corrective_action": "控制焊料量",
            "family": "fc-bump-open-short", "synonym_of": None,
            "coverage": "FC 互连短路（焊料量/塌陷）；与 bump open 形成干扰",
        },
    },
    {
        "case_id": "LC009",
        "product_id": "PROD_010",
        "abnormal_types": ("00031",),
        "abnormal_processes": ("P005",),
        "abnormal_description": "客户端功能测试发现 FC 器件互连短路，显微复查显示个别 bump 位置偏移后与相邻 bump "
                                "焊料搭接，表现为 bump short；异常位于 Flip Chip Attach 接合界面。",
        "root_cause": "结案确认：FC placement偏移，造成 bump 与相邻 bump 焊料搭接。",
        "corrective_action": "优化FC placement和reflow，并保证接合共面性。",
        "detail": {
            "detail_id": "LD009", "production_lot": "DEV_PL_108", "customer_lot": "DEV_CL_108",
            "production_time": "2026-07-20", "detection_stage": "Customer", "detection_time": "2026-08-05",
            "affected_qty": 220, "disposition": "本事件纳入处置范围的产品全部隔离并报废。",
        },
        "evidences": (
            {
                "checkpoint_id": "LE118", "checkpoint_type": "Production", "custom_name": None,
                "result": "Flip Chip Attach 设备 {equipment} 的 placement 偏移记录超出规格，"
                          "偏移方向与搭接位置一致。",
                "relevance": "related", "equipment_process": "P005",
            },
            {
                "checkpoint_id": "LE119", "checkpoint_type": "QC", "custom_name": None,
                "result": "显微复查确认 bump 桥连方向与 placement 偏移方向一致，同一器件其它 bump 间距正常。",
                "relevance": "related", "equipment_process": None,
            },
        ),
        "source": {
            "failure_mode_id": "00031", "root_cause": "FC placement偏移",
            "corrective_action": "优化FC placement和reflow",
            "family": "fc-bump-open-short", "synonym_of": None,
            "coverage": "FC 短路的 placement 偏移依据；与同族 open 案例共用产品族",
        },
    },
)

# 五条 Query 的当前已知事实；`batch_basis` 记录批号是复用历史批还是当前新批。
QUERIES = (
    {
        "query_id": "LQ001", "product_id": "PROD_014",
        "production_lot": "DEV_PL_109", "customer_lot": "DEV_CL_109", "batch_basis": "new",
        "text": "LF_WB 产品 PROD_014 在 OQC 发现芯片贴装面倾斜，X-ray 剖面显示对角胶层厚度差超出规格，"
                "涉及客户 CUS_002、生产批 DEV_PL_109、客户批 DEV_CL_109；"
                "同批 leadframe 来料平整度抽检与外观复查均正常，尚未确认原因。",
    },
    {
        "query_id": "LQ002", "product_id": "PROD_008",
        "production_lot": "DEV_PL_110", "customer_lot": "DEV_CL_110", "batch_basis": "new",
        "text": "客户反馈基板类产品 PROD_008 内部芯片与载体不平行，声学扫描显示单边胶层偏厚，"
                "涉及客户 CUS_003、生产批 DEV_PL_110、客户批 DEV_CL_110；"
                "已排除外观损伤，原因尚未确认。",
    },
    {
        "query_id": "LQ003", "product_id": "PROD_007",
        "production_lot": "DEV_PL_102", "customer_lot": "DEV_CL_102", "batch_basis": "reused_historical",
        "text": "PROD_007 生产批 DEV_PL_102（客户批 DEV_CL_102，涉及客户 CUS_003）在客户端复查时发现封装整体翘曲，"
                "器件呈碗形变形、焊球共面性超出规格；已排除运输与搬运损伤，包装与外观检查未见磕碰，原因尚未确认。",
    },
    {
        "query_id": "LQ004", "product_id": "PROD_012",
        "production_lot": "DEV_PL_111", "customer_lot": "DEV_CL_111", "batch_basis": "new",
        "text": "FC 产品 PROD_012 在 In-process 电性测试发现互连开路，X-ray 显示个别 bump 未与 substrate pad 接合，"
                "涉及客户 CUS_005、生产批 DEV_PL_111、客户批 DEV_CL_111；AOI 未发现异物污染，原因尚未确认。",
    },
    {
        "query_id": "LQ005", "product_id": "PROD_017",
        "production_lot": "DEV_PL_112", "customer_lot": "DEV_CL_112", "batch_basis": "new",
        "text": "FC 产品 PROD_017 在功能测试发现互连短路，显微复查显示相邻 bump 焊料搭接，"
                "涉及客户 CUS_004、生产批 DEV_PL_112、客户批 DEV_CL_112；原因尚未确认。",
    },
)

# 45 对逐对标签建议：(query_id, case_id, 建议标签或 None, 双侧事实理由, 字段/ID 证据)。
# None 表示草稿阶段不确定，须由用户在 SD3 裁决；正式 qrels 只接受整数 0/1。
JUDGMENTS = (
    ("LQ001", "LC001", 1,
     "双侧都是 PROD_014（LF_WB）在 OQC 发现芯片贴装面倾斜与对角胶层厚度差，异常相同、产品与路线相同，"
     "是本次最直接的历史参考。",
     ("Query.product_id=PROD_014", "LC001.detail.product_id=PROD_014", "LC001.detail.abnormal_types=00004")),
    ("LQ001", "LC002", 1,
     "LC002 的异常同为 die tilt（贴装面倾斜），只是路线（SUBSTRATE_WB）与措辞（声学扫描）不同；"
     "规则不要求措辞逐字相同，异常相同即具备调查参考价值。",
     ("Query 描述“芯片贴装面倾斜”", "LC002.detail.abnormal_types=00004", "LC002.source.failure_mode_id=00004")),
    ("LQ001", "LC003", 1,
     "LC003 的异常集合含 00004 die tilt，与 LQ001 异常相同；其产品与路线不同只作背景补充，"
     "不单独决定相关性，但异常参考价值成立。",
     ("LC003.detail.abnormal_types=00004,00022", "LC003.source.failure_mode_id=00004")),
    ("LQ001", "LC004", 0,
     "LC004 的异常是 package warpage（封装整体翘曲），与 LQ001 的局部 die tilt 不是同一异常；"
     "同属几何类异常或同族都不自动等于同异常。",
     ("LC004.detail.abnormal_types=00022", "Query 描述“局部贴装面倾斜”")),
    ("LQ001", "LC005", 0,
     "LC005 同为 package warpage，且产品与路线均与 LQ001 不同；仅有通用调查方法不构成相关。",
     ("LC005.detail.abnormal_types=00022", "LC005.detail.product_id=PROD_007")),
    ("LQ001", "LC006", 0,
     "LC006 是 FC 互连开路（bump open），与 LQ001 的 die tilt 机制与站点都不同。",
     ("LC006.detail.abnormal_types=00030", "LC006.detail.product_id=PROD_012")),
    ("LQ001", "LC007", 0,
     "LC007 同为 FC 开路，与 LQ001 的 die tilt 无关。",
     ("LC007.detail.abnormal_types=00030", "LC007.detail.product_id=PROD_016")),
    ("LQ001", "LC008", 0,
     "LC008 是 FC 互连短路（bump short），与 LQ001 的 die tilt 无关。",
     ("LC008.detail.abnormal_types=00031", "LC008.detail.product_id=PROD_017")),
    ("LQ001", "LC009", 0,
     "LC009 同为 FC 短路，与 LQ001 的 die tilt 无关。",
     ("LC009.detail.abnormal_types=00031", "LC009.detail.product_id=PROD_010")),
    ("LQ002", "LC001", 1,
     "LQ002 与 LC001 是同一异常 die tilt 的不同表达（LC001 用 X-ray 剖面描述，LQ002 用声学扫描描述）；"
     "跨产品与路线仍有调查参考价值。",
     ("LC001.detail.abnormal_types=00004", "LC001.source.failure_mode_id=00004")),
    ("LQ002", "LC002", 1,
     "LC002 的贴装面倾斜同样由声学扫描发现，与 LQ002 的观测方式与异常均一致。",
     ("LC002.detail.abnormal_types=00004", "LC002.detail.product_id=PROD_007")),
    ("LQ002", "LC003", 1,
     "LC003 与 LQ002 同为产品 PROD_008、同为基板路线，且异常集合含 00004 die tilt；"
     "异常相同且背景相同，参考价值最高。",
     ("LC003.detail.product_id=PROD_008", "LC003.detail.abnormal_types=00004,00022")),
    ("LQ002", "LC004", None,
     "LC004 与 LQ002 同为产品 PROD_008，但 LC004 的异常只有 package warpage，与 LQ002 的 die tilt 不同。"
     "同产品背景不单独决定相关性，本对是否采用待用户裁决。",
     ("LC004.detail.product_id=PROD_008", "LC004.detail.abnormal_types=00022")),
    ("LQ002", "LC005", 0,
     "LC005 为 package warpage，产品与路线也与 LQ002 不同，异常不相同。",
     ("LC005.detail.abnormal_types=00022", "LC005.detail.product_id=PROD_007")),
    ("LQ002", "LC006", 0,
     "LC006 为 FC 互连开路，与 LQ002 的 die tilt 不同。",
     ("LC006.detail.abnormal_types=00030",)),
    ("LQ002", "LC007", 0,
     "LC007 同为 FC 开路，与 LQ002 无关。",
     ("LC007.detail.abnormal_types=00030",)),
    ("LQ002", "LC008", 0,
     "LC008 为 FC 短路，与 LQ002 无关。",
     ("LC008.detail.abnormal_types=00031",)),
    ("LQ002", "LC009", 0,
     "LC009 同为 FC 短路，与 LQ002 无关。",
     ("LC009.detail.abnormal_types=00031",)),
    ("LQ003", "LC001", 0,
     "LC001 为 die tilt，与 LQ003 的封装整体翘曲不是同一异常。",
     ("LC001.detail.abnormal_types=00004",)),
    ("LQ003", "LC002", None,
     "LC002 与 LQ003 同产品 PROD_007、同生产批 DEV_PL_102、同客户批 DEV_CL_102，"
     "但 LC002 的异常是 die tilt，与 LQ003 的 package warpage 不同。"
     "同批次背景不自动产生正例，本对是否采用待用户裁决。",
     ("LC002.detail.production_lot=DEV_PL_102", "LC002.detail.abnormal_types=00004",
      "Query.production_lot=DEV_PL_102")),
    ("LQ003", "LC003", 1,
     "LC003 的异常集合含 00022 package warpage，与 LQ003 异常相同。",
     ("LC003.detail.abnormal_types=00004,00022", "LC003.source.additional_failure_modes=00022")),
    ("LQ003", "LC004", 1,
     "LC004 的异常同为 package warpage（封装整体弓形翘曲），跨产品仍有调查参考价值。",
     ("LC004.detail.abnormal_types=00022", "LC004.source.failure_mode_id=00022")),
    ("LQ003", "LC005", 1,
     "LC005 与 LQ003 同产品 PROD_007、同生产批 DEV_PL_102、同客户批 DEV_CL_102，"
     "且异常同为 package warpage；异常与背景同时成立。",
     ("LC005.detail.production_lot=DEV_PL_102", "LC005.detail.abnormal_types=00022")),
    ("LQ003", "LC006", 0,
     "LC006 为 FC 互连开路，与 LQ003 的翘曲无关。",
     ("LC006.detail.abnormal_types=00030",)),
    ("LQ003", "LC007", 0,
     "LC007 同为 FC 开路，与 LQ003 无关。",
     ("LC007.detail.abnormal_types=00030",)),
    ("LQ003", "LC008", 0,
     "LC008 为 FC 短路，与 LQ003 无关。",
     ("LC008.detail.abnormal_types=00031",)),
    ("LQ003", "LC009", 0,
     "LC009 同为 FC 短路，与 LQ003 无关。",
     ("LC009.detail.abnormal_types=00031",)),
    ("LQ004", "LC001", 0,
     "LC001 为 die tilt，与 LQ004 的 FC 互连开路既不同异常也不同路线。",
     ("LC001.detail.abnormal_types=00004",)),
    ("LQ004", "LC002", 0,
     "LC002 同为 die tilt，与 LQ004 的 FC 开路无关。",
     ("LC002.detail.abnormal_types=00004",)),
    ("LQ004", "LC003", 0,
     "LC003 为 die tilt 与 package warpage，与 LQ004 的 bump open 不同。",
     ("LC003.detail.abnormal_types=00004,00022",)),
    ("LQ004", "LC004", 0,
     "LC004 为 package warpage，与 LQ004 的 bump open 不同。",
     ("LC004.detail.abnormal_types=00022",)),
    ("LQ004", "LC005", 0,
     "LC005 同为 package warpage，与 LQ004 无关。",
     ("LC005.detail.abnormal_types=00022",)),
    ("LQ004", "LC006", 1,
     "LC006 与 LQ004 同为产品 PROD_012（SUBSTRATE_FC），且异常同为 bump open；"
     "异常相同、产品与路线相同，参考价值最高。",
     ("LC006.detail.product_id=PROD_012", "LC006.detail.abnormal_types=00030",
      "Query.product_id=PROD_012")),
    ("LQ004", "LC007", 1,
     "LC007 的异常同为 bump open（互连未接合开路），跨产品仍有调查参考价值。",
     ("LC007.detail.abnormal_types=00030", "LC007.source.failure_mode_id=00030")),
    ("LQ004", "LC008", 0,
     "LC008 是 bump short（相邻 bump 桥连），与 LQ004 的 bump open 方向相反；"
     "同属 FC 互连族不自动等于同异常。",
     ("LC008.detail.abnormal_types=00031", "Query 描述“互连开路”")),
    ("LQ004", "LC009", 0,
     "LC009 同为 bump short，与 LQ004 的 bump open 不同。",
     ("LC009.detail.abnormal_types=00031",)),
    ("LQ005", "LC001", 0,
     "LC001 为 die tilt，与 LQ005 的 FC 互连短路无关。",
     ("LC001.detail.abnormal_types=00004",)),
    ("LQ005", "LC002", 0,
     "LC002 同为 die tilt，与 LQ005 无关。",
     ("LC002.detail.abnormal_types=00004",)),
    ("LQ005", "LC003", 0,
     "LC003 为 die tilt 与 package warpage，与 LQ005 的 bump short 不同。",
     ("LC003.detail.abnormal_types=00004,00022",)),
    ("LQ005", "LC004", 0,
     "LC004 为 package warpage，与 LQ005 不同。",
     ("LC004.detail.abnormal_types=00022",)),
    ("LQ005", "LC005", 0,
     "LC005 同为 package warpage，与 LQ005 的 bump short 不同。",
     ("LC005.detail.abnormal_types=00022",)),
    ("LQ005", "LC006", 0,
     "LC006 是 bump open（未接合开路），与 LQ005 的 bump short 方向相反，是同族干扰项。",
     ("LC006.detail.abnormal_types=00030", "Query 描述“焊料搭接短路”")),
    ("LQ005", "LC007", 0,
     "LC007 同为 bump open，与 LQ005 的 bump short 不同。",
     ("LC007.detail.abnormal_types=00030",)),
    ("LQ005", "LC008", 1,
     "LC008 与 LQ005 同为产品 PROD_017（SUBSTRATE_FC），且异常同为 bump short；"
     "异常相同、产品与路线相同。",
     ("LC008.detail.product_id=PROD_017", "LC008.detail.abnormal_types=00031",
      "Query.product_id=PROD_017")),
    ("LQ005", "LC009", 1,
     "LC009 的异常同为 bump short（相邻 bump 焊料搭接），跨产品仍有调查参考价值。",
     ("LC009.detail.abnormal_types=00031", "LC009.source.failure_mode_id=00031")),
)


# 2026-10-08 用户对两个待裁决配对的最终裁决。草稿建议为 None 的两对必须在这里有值，
# 否则 `--publish-qrels` 拒绝发布。裁决理由见 README 与 qrels.json 的 user_decisions。
USER_GT_DECISIONS = {
    ("LQ002", "LC004"): 0,
    ("LQ003", "LC002"): 1,
}
# 用户对 ② 的说明：同产品且同生产批/同客户批的背景足以采用，即使异常不同。
USER_GT_NOTES = {
    ("LQ003", "LC002"): "用户裁决：同一生产批 DEV_PL_102 的背景足以采用，即使历史案例的异常与当前 Query 不同。",
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_equipment_processes(reference_path: Path) -> dict[str, str]:
    """读主数据 equipment 表，返回 equipment_id → process_id；只用于确定证据里的设备事实。"""
    from openpyxl import load_workbook

    workbook = load_workbook(reference_path, read_only=True, data_only=True)
    try:
        rows = workbook["equipment"].iter_rows(values_only=True)
        headers = next(rows)
        if headers.count("equipment_id") != 1 or headers.count("process_id") != 1:
            raise ValueError("主数据 equipment 缺少 equipment_id 或 process_id 列")
        id_at, process_at = headers.index("equipment_id"), headers.index("process_id")
        table = {}
        for values in rows:
            if values[id_at] is None:
                continue
            table[str(values[id_at])] = str(values[process_at])
    finally:
        workbook.close()
    if not table:
        raise ValueError("主数据 equipment 表为空")
    return table


def _choose_equipment(rng: random.Random, table: dict[str, str], process_id: str) -> str:
    candidates = sorted(key for key, process in table.items() if process == process_id)
    if not candidates:
        raise ValueError(f"主数据中没有适用于工序 {process_id} 的设备，无法确定证据中的设备事实")
    return rng.choice(candidates)


def build_corpus(
    reference: ReferenceData, equipment_processes: dict[str, str], *, seed: int = SEED,
) -> dict:
    """按事实表组装语料；文本字段只描述已确定的事实。"""
    rng = random.Random(seed)
    cases, details, evidences = [], [], []
    sources: dict[str, dict] = {}
    family_cases: dict[str, list[str]] = {}

    for spec in CASES:
        case_id = spec["case_id"]
        cases.append({
            "case_id": case_id,
            "abnormal_description": spec["abnormal_description"],
            "root_cause": spec["root_cause"],
            "corrective_action": spec["corrective_action"],
            "investigation_others": None,
            "abnormal_processes": list(spec["abnormal_processes"]),
        })
        details.append({
            "detail_id": spec["detail"]["detail_id"],
            "case_id": case_id,
            "product_id": spec["product_id"],
            "customer_lot": spec["detail"]["customer_lot"],
            "production_lot": spec["detail"]["production_lot"],
            "production_time": spec["detail"]["production_time"],
            "detection_stage": spec["detail"]["detection_stage"],
            "detection_time": spec["detail"]["detection_time"],
            "abnormal_types": list(spec["abnormal_types"]),
            "affected_qty": spec["detail"]["affected_qty"],
            "disposition": spec["detail"]["disposition"],
        })
        for item in spec["evidences"]:
            process_id = item["equipment_process"]
            equipment = _choose_equipment(rng, equipment_processes, process_id) if process_id else None
            evidences.append({
                "checkpoint_id": item["checkpoint_id"],
                "case_id": case_id,
                "checkpoint_type": item["checkpoint_type"],
                "custom_name": item["custom_name"],
                "result": item["result"].format(equipment=equipment or ""),
                "relevance": item["relevance"],
            })

        source = spec["source"]
        generation_note = {
            "date": "2026-10-08",
            "family": source["family"],
            "synonym_of": source["synonym_of"],
            "coverage": source["coverage"],
            "isolated_from_development": True,
        }
        if "additional_failure_modes" in source:
            generation_note["additional_failure_modes"] = [
                dict(row) for row in source["additional_failure_modes"]
            ]
        sources[case_id] = {
            "sheet": "failure_modes",
            "failure_mode_id": source["failure_mode_id"],
            "root_cause": source["root_cause"],
            "corrective_action": source["corrective_action"],
            "closure_status": "confirmed",
            "review_status": REVIEW_STATUS,
            "generation_note": generation_note,
        }
        family_cases.setdefault(source["family"], []).append(case_id)

    queries = [
        {"query_id": row["query_id"], "known_at": QUERY_KNOWN_AT, "text": row["text"]}
        for row in QUERIES
    ]
    return {
        "split": SPLIT,
        "review_status": REVIEW_STATUS,
        "cases": cases,
        "details": details,
        "evidences": evidences,
        "groups": [],
        "memberships": [],
        "sources": sources,
        "queries": queries,
        "corpus_version": CORPUS_VERSION,
        "availability_snapshot": {
            "snapshot_id": SNAPSHOT_ID,
            "complete_available_on": COMPLETE_AVAILABLE_ON,
            "basis": SNAPSHOT_BASIS,
            "query_known_at": QUERY_KNOWN_AT,
        },
        "generation_basis": (
            "GR-10：产品、工序、批号、时间、数量、Failure Mode、Case.abnormal_processes、"
            "Evidence 类型与 relevance、原因/措施候选及证据中的 equipment_id 由 "
            "scripts/prepare_locked_test_v1.py 从主数据确定；文本字段只描述这些已确定的事实，"
            "脚本不调用任何模型服务。"
        ),
        "generation_review": {
            "date": "2026-10-08",
            "script": "scripts/prepare_locked_test_v1.py",
            "seed": SEED,
            "families": [
                {"family": family, "cases": members, "policy": "整族仅用于 Locked Test",
                 "note": "家族关系不构成检索相关性"}
                for family, members in family_cases.items()
            ],
            "isolation": (
                "新四条来源 00004 / 00022 / 00030 / 00031 与开发已用来源 "
                "00010 / 00016 / 00018 / 00026 / 00028 不重合；新 Case 产品均未出现在开发 Case 或开发 Query 中。"
                "这是同一合成知识底座下的来源/家族隔离，小样本不证明真实现场泛化。"
            ),
            "automated_scope": (
                "已由确定性代码覆盖：版本与哈希绑定、ID 唯一、Query × Case 完整配对、确认状态与 split 守卫、"
                "批号固定属性（CR-08～10）、异常站点与产品路线并集（CR-49）、生成限制（GR-01/02/04/06）、"
                "来源记录与主数据候选一致。"
            ),
            "manual_scope": (
                "未自动化：同义异常、易混淆对与弱相关边界依赖逐对人工判断；qrels 全部 45 对待用户确认，"
                "源 Case 的 review_status 保持 draft_pending_human_review。"
            ),
        },
        "query_basis": {
            "rule": "每条 Query 写明当时已知的客户、产品、生产批号与客户批号；取值与主数据及语料一致。",
            "known_at": QUERY_KNOWN_AT,
            "reused_batches": [
                {"production_lot": "DEV_PL_102", "customer_lot": "DEV_CL_102", "product_id": "PROD_007",
                 "used_by": "LQ003", "basis": "复用历史批 DEV_PL_102 作已知背景；同产品、同投批时间、同客户批。"}
            ],
            "new_batches": ["DEV_PL_109", "DEV_PL_110", "DEV_PL_111", "DEV_PL_112"],
            "note": "同批背景不自动产生正例；新批号不与 Development 或本语料的 Case 批号重复。",
        },
    }


def self_check(payload: dict) -> None:
    """核对固定规模、批号复用与完整配对；失败直接报错，不写文件。"""
    cases = [case["case_id"] for case in payload["cases"]]
    details = payload["details"]
    queries = [query["query_id"] for query in payload["queries"]]
    if len(cases) != 9 or len(set(cases)) != 9:
        raise ValueError(f"固定规模要求 9 个 Case，当前 {len(cases)}")
    if len(details) != 9:
        raise ValueError(f"固定规模要求 9 个 Detail，当前 {len(details)}")
    if len(payload["evidences"]) < 18:
        raise ValueError(f"固定规模要求至少 18 个 Evidence，当前 {len(payload['evidences'])}")
    if len(queries) != 5:
        raise ValueError(f"固定规模要求 5 条 Query，当前 {len(queries)}")
    if len(JUDGMENTS) != len(queries) * len(cases):
        raise ValueError(f"完整配对要求 {len(queries) * len(cases)} 对，当前 {len(JUDGMENTS)}")

    counts: dict[str, int] = {}
    for detail in details:
        counts[detail["production_lot"]] = counts.get(detail["production_lot"], 0) + 1
    reused = sorted(lot for lot, count in counts.items() if count >= 2)
    if reused != ["DEV_PL_102"] or counts["DEV_PL_102"] != 2:
        raise ValueError(f"GR-04 要求恰一个复用批号出现两次，当前 {counts}")

    case_lots = {detail["production_lot"] for detail in details}
    for batch in payload["query_basis"]["new_batches"]:
        if batch in case_lots:
            raise ValueError(f"Query 新批号 {batch} 与 Case 批号重复")
    pairs = {(row[0], row[1]) for row in JUDGMENTS}
    if pairs != {(query, case) for query in queries for case in cases}:
        raise ValueError("qrels 草稿未完整覆盖 Query × Case 的全部配对")

    per_case = {case: 0 for case in cases}
    for evidence in payload["evidences"]:
        per_case[evidence["case_id"]] += 1
    thin = sorted(case for case, count in per_case.items() if count < 2)
    if thin:
        raise ValueError(f"每 Case 至少两个真实调查项，当前不足：{thin}")


def build_qrels_draft(payload: dict, *, corpus_path: Path, reference_path: Path) -> dict:
    """按草稿标签建议生成 qrels 草稿；不确定项保持 null 并列入待裁决问题。"""
    rows, pending = [], []
    for query_id, case_id, relevance, rationale, evidence in JUDGMENTS:
        rows.append({
            "query_id": query_id,
            "case_id": case_id,
            "relevance": relevance,
            "rationale": rationale,
            "evidence": list(evidence),
            "origin": "agent_drafted_pending_user_confirmation",
        })
        if relevance is None:
            pending.append({
                "query_id": query_id,
                "case_id": case_id,
                "question": rationale,
                "evidence": list(evidence),
            })
    return {
        "qrels_version": QRELS_VERSION,
        "split": SPLIT,
        "review_status": REVIEW_STATUS,
        "status": "draft",
        "rationale_author": "agent_drafted_pending_user_confirmation",
        "confirmed_on": None,
        "confirmation_scope": None,
        "sources": {
            "dataset": {"path": CORPUS_RELATIVE, "sha256": sha256_of(corpus_path)},
            "reference": {"path": REFERENCE_RELATIVE, "sha256": sha256_of(reference_path)},
        },
        "label_meanings": {"0": "Not Relevant", "1": "Relevant",
                           "null": "草稿阶段不确定，须由用户裁决"},
        "label_policy": (
            "二值标签依据 Current Plan §4：是否 Relevant 取决于当前已知异常与历史案例的调查参考价值；"
            "同批次/同产品/同产品族/同客户等背景不单独决定相关性，共享 failure_mode_id 也不自动等于同异常。"
        ),
        "confirmation_required": (
            "全部 45 对须由用户确认；确认前不发布正式 qrels.json、不冻结、不运行真实 Locked Test 排名。"
            "正式 evaluator 会以 review_status 拒绝本草稿。"
        ),
        "pending_questions": pending,
        "judgments": rows,
    }


def build_qrels(
    payload: dict, *, corpus_path: Path, reference_path: Path, confirmed_on: str,
) -> dict:
    """在草稿建议上应用用户裁决，生成正式 qrels；全部标签必须是整数 0 或 1。"""
    rows, decisions = [], []
    for query_id, case_id, draft_relevance, rationale, evidence in JUDGMENTS:
        relevance = USER_GT_DECISIONS.get((query_id, case_id), draft_relevance)
        if type(relevance) is not int or relevance not in (0, 1):
            raise ValueError(
                f"({query_id}, {case_id}) 没有可用的用户裁决（当前 {relevance!r}），不能发布正式 qrels"
            )
        rows.append({
            "query_id": query_id,
            "case_id": case_id,
            "relevance": relevance,
            "rationale": rationale,
            "evidence": list(evidence),
            "origin": "user_confirmed",
        })
        if draft_relevance is None:
            decisions.append({
                "query_id": query_id,
                "case_id": case_id,
                "draft_relevance": draft_relevance,
                "confirmed_relevance": relevance,
                "decision_by": "user",
                "decision_note": USER_GT_NOTES.get((query_id, case_id), "用户裁决：采用草稿倾向。"),
                "draft_rationale": rationale,
            })
    if len(rows) != len(payload["queries"]) * len(payload["cases"]):
        raise ValueError(f"正式 qrels 必须是完整配对，当前 {len(rows)} 对")
    return {
        "qrels_version": QRELS_VERSION,
        "split": SPLIT,
        "review_status": "human_confirmed",
        "confirmed_on": confirmed_on,
        "confirmation_scope": "locked_test_v1_corpus_and_all_45_binary_labels",
        "rationale_author": "agent_drafted_user_confirmed",
        "sources": {
            "dataset": {"path": CORPUS_RELATIVE, "sha256": sha256_of(corpus_path)},
            "reference": {"path": REFERENCE_RELATIVE, "sha256": sha256_of(reference_path)},
        },
        "label_meanings": {"0": "Not Relevant", "1": "Relevant"},
        "label_policy": (
            "二值标签依据 Current Plan §4：是否 Relevant 取决于当前已知异常与历史案例的调查参考价值。"
            "2026-10-08 用户裁决 (LQ003, LC002) = 1：同产品且同生产批/同客户批的背景在该对中被判定为足以采用——"
            "这与 §4 现行文字“背景不单独决定相关性”不一致，按用户裁决保留并记录为决策差异，不改规则文字。"
        ),
        "user_decisions": decisions,
        "judgments": rows,
    }


def validate_corpus(payload: dict, reference_path: Path) -> None:
    """用既有加载器在临时文件上校验语料；不触碰目标文件。"""
    with tempfile.TemporaryDirectory() as directory:
        temp_path = Path(directory) / "corpus-v1.json"
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        records, loaded, reference = load_validated_dataset(temp_path, reference_path)
        check_source_records(records, loaded, reference)


def write_json(path: Path, payload: dict) -> Path:
    """先写同目录临时文件再原子替换，失败不留下半份文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f"{path.name}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, path)
        # NamedTemporaryFile 默认 0600；显式对齐仓库其余数据文件的权限。
        os.chmod(path, 0o644)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return path


def guard_target(path: Path, *, force: bool) -> None:
    """默认保护已有文件；正式 qrels 只通过显式 `--publish-qrels` 发布。"""
    if path.exists() and not force:
        raise SystemExit(f"目标已存在，拒绝覆盖（需要时用 --force）：{path}")


def publish_qrels(
    output_dir: Path, reference_path: Path, *, confirmed_on: str, force: bool,
) -> int:
    """发布正式 qrels：要求语料已生成、确认日期合法、目标未被占用。"""
    try:
        date.fromisoformat(confirmed_on)
    except ValueError as error:
        raise SystemExit(f"--confirmed-on 必须是 YYYY-MM-DD：{error}") from error
    corpus_path = output_dir / CORPUS_RELATIVE
    if not corpus_path.is_file():
        raise SystemExit(f"语料不存在，请先运行生成步骤：{corpus_path}")
    qrels_path = output_dir / QRELS_RELATIVE
    guard_target(qrels_path, force=force)

    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    self_check(payload)
    qrels = build_qrels(
        payload, corpus_path=corpus_path, reference_path=reference_path, confirmed_on=confirmed_on,
    )
    write_json(qrels_path, qrels)

    positives = {
        query["query_id"]: sum(
            1 for row in qrels["judgments"]
            if row["query_id"] == query["query_id"] and row["relevance"] == 1
        )
        for query in payload["queries"]
    }
    print(f"正式 qrels：{qrels_path}")
    print(f"  {len(qrels['judgments'])} 对 0/1；review_status={qrels['review_status']}；"
          f"confirmed_on={qrels['confirmed_on']}")
    print(f"  正例：{positives}")
    print(f"  用户裁决差异：{len(qrels['user_decisions'])} 对；草稿文件保留未改。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="生成 locked-test-v1 语料与 qrels 草稿；正式 qrels 须显式 --publish-qrels",
    )
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT,
                        help="输出根目录；默认仓库根目录，可指向沙盒目录")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的目标文件")
    parser.add_argument("--publish-qrels", action="store_true",
                        help="在用户确认后发布正式 qrels.json；需要 --confirmed-on")
    parser.add_argument("--confirmed-on", help="用户确认日期 YYYY-MM-DD；仅 --publish-qrels 使用")
    args = parser.parse_args(argv)

    output_dir = args.output_dir.resolve()
    reference_path = PROJECT_ROOT / REFERENCE_RELATIVE
    corpus_path = output_dir / CORPUS_RELATIVE
    draft_path = output_dir / QRELS_DRAFT_RELATIVE

    if args.publish_qrels:
        if not args.confirmed_on:
            raise SystemExit("--publish-qrels 需要 --confirmed-on YYYY-MM-DD")
        return publish_qrels(
            output_dir, reference_path, confirmed_on=args.confirmed_on, force=args.force,
        )

    guard_target(corpus_path, force=args.force)
    guard_target(draft_path, force=args.force)

    reference = load_reference(reference_path)
    equipment_processes = read_equipment_processes(reference_path)
    payload = build_corpus(reference, equipment_processes)
    self_check(payload)
    validate_corpus(payload, reference_path)
    write_json(corpus_path, payload)

    qrels = build_qrels_draft(payload, corpus_path=corpus_path, reference_path=reference_path)
    write_json(draft_path, qrels)

    print(f"语料：{corpus_path}")
    print(f"  {len(payload['cases'])} Case / {len(payload['details'])} Detail / "
          f"{len(payload['evidences'])} Evidence / {len(payload['queries'])} Query")
    print(f"  split={payload['split']}；snapshot={payload['availability_snapshot']['snapshot_id']}")
    print(f"qrels 草稿：{draft_path}")
    print(f"  {len(qrels['judgments'])} 对，其中待用户裁决 {len(qrels['pending_questions'])} 对；"
          f"review_status={qrels['review_status']}")
    print("正式 qrels.json 未发布；正式 evaluator 会拒绝草稿。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
