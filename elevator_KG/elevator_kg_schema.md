# Elevator KG Schema

## Node Kinds

| kind | count | 中文 |
|---|---:|---|
| `action` | 14 | 处置动作 |
| `asset` | 1 | 资产 |
| `component` | 31 | 部件 |
| `dataset` | 2 | 数据集 |
| `elevator` | 199 | 电梯 |
| `fault_category` | 11 | 故障类别 |
| `fault_location` | 8 | 故障位置 |
| `fault_phenomenon` | 56 | 故障现象 |
| `maintenance_unit` | 137 | 维保单位 |
| `manufacturer` | 79 | 制造单位 |
| `part_type` | 120 | 更换部件类型 |
| `place` | 199 | 地点 |
| `raw_fault_text` | 538 | 原始故障文本 |
| `rule` | 5 | 法规/标准 |
| `safety_topic` | 6 | 安全主题 |
| `site_type` | 8 | 使用场所 |
| `source` | 7 | 资料来源 |
| `system` | 11 | 系统 |
| `work_order` | 2140 | 救援工单 |

## Relationship Types

| relation | count | 中文 |
|---|---:|---|
| `BELONGS_TO_SYSTEM` | 31 | 属于系统 |
| `CATEGORIZED_AS` | 538 | 归类为 |
| `CAUSES_PHENOMENON` | 27 | 导致现象 |
| `CHECKS_COMPONENT` | 2 | 检查部件 |
| `COVERS_SAFETY_TOPIC` | 8 | 覆盖安全主题 |
| `DEFINES_MAINTENANCE_SCOPE` | 1 | 定义维保范围 |
| `DERIVED_FROM` | 2141 | 来源于 |
| `HANDLED_BY` | 2114 | 处置单位 |
| `HAS_AGGREGATE_CAUSE` | 496 | 聚合故障原因 |
| `HAS_COMPONENT` | 31 | 包含部件 |
| `HAS_FAULT_CATEGORY` | 2132 | 故障归类 |
| `HAS_FAULT_LOCATION` | 8 | 故障位置 |
| `HAS_FAULT_PHENOMENON` | 5577 | 故障现象 |
| `HAS_RAW_FAULT_TEXT` | 2132 | 原始故障文本 |
| `HAS_REPLACED_PART_TYPE` | 120 | 更换部件类型 |
| `HAS_ROOT_COMPONENT` | 33 | 关联关键部件 |
| `HAS_SITE_TYPE` | 199 | 使用场所 |
| `HAS_SYSTEM` | 11 | 包含系统 |
| `LIKELY_AFFECTS` | 11 | 可能影响 |
| `LOCATED_AT` | 2339 | 位于 |
| `MAINTAINED_BY` | 197 | 维保单位 |
| `MANUFACTURED_BY` | 199 | 制造单位 |
| `MAPS_TO_COMPONENT` | 41 | 映射到部件 |
| `MAPS_TO_SYSTEM` | 8 | 映射到系统 |
| `MITIGATES` | 15 | 缓解/消除 |
| `OBSERVED_PHENOMENON` | 54 | 观测到现象 |
| `PART_OF_SAFETY_CHAIN` | 10 | 属于安全链 |
| `RECOMMENDS_ACTION` | 22 | 建议处置 |
| `REPORTED_ON` | 2140 | 报修对象 |
| `SUPPORTS_CATEGORY` | 8 | 支撑故障类别 |

## Traceability Path Examples

- `work_order -> HAS_FAULT_CATEGORY -> fault_category -> LIKELY_AFFECTS -> system`
- `work_order -> HAS_RAW_FAULT_TEXT -> raw_fault_text -> CATEGORIZED_AS -> fault_category`
- `fault_category -> HAS_ROOT_COMPONENT -> component -> BELONGS_TO_SYSTEM -> system`
- `fault_category -> CAUSES_PHENOMENON -> fault_phenomenon`
- `fault_category -> RECOMMENDS_ACTION -> action`
- `rule/source -> SUPPORTS_CATEGORY/COVERS_SAFETY_TOPIC -> category/topic`
