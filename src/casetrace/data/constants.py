"""固定枚举：来源为数据结构文档 §2、§3 和 CR-42。"""

DETECTION_STAGES = ("IQC", "In-process", "OQC", "Customer", "Other")

CHECKPOINT_TYPES = (
    "QC", "AOI", "Production", "OCAP", "Previous/Next Lot",
    "Monitoring", "EDX", "Reliability", "Material", "Other",
)

RELEVANCE_VALUES = ("related", "not_related", "uncertain")

GROUP_TYPES = (
    "repeat_case", "same_abnormal_process", "project", "customer_request", "management_request", "other",
)
