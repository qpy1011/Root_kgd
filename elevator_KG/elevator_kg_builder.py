from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEPS_DIR = BASE_DIR / ".deps"
if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))


NODE_FIELDS = [
    "id",
    "label",
    "name",
    "name_en",
    "kind",
    "kind_zh",
    "description",
    "source",
    "source_url",
    "count",
    "weight",
    "trapped_people",
    "rescue_minutes",
    "color",
    "size",
]

EDGE_FIELDS = [
    "source",
    "target",
    "relation",
    "relation_zh",
    "evidence",
    "source_doc",
    "source_url",
    "count",
    "weight",
    "color",
]

KIND_ZH = {
    "asset": "资产",
    "system": "系统",
    "component": "部件",
    "fault_category": "故障类别",
    "fault_phenomenon": "故障现象",
    "raw_fault_text": "原始故障文本",
    "action": "处置动作",
    "rule": "法规/标准",
    "safety_topic": "安全主题",
    "dataset": "数据集",
    "work_order": "救援工单",
    "elevator": "电梯",
    "place": "地点",
    "site_type": "使用场所",
    "organization": "组织",
    "manufacturer": "制造单位",
    "maintenance_unit": "维保单位",
    "fault_location": "故障位置",
    "part_type": "更换部件类型",
    "source": "资料来源",
}

KIND_STYLE = {
    "asset": ("#334155", 14),
    "system": ("#2563eb", 12),
    "component": ("#0891b2", 9),
    "fault_category": ("#dc2626", 11),
    "fault_phenomenon": ("#ea580c", 9),
    "raw_fault_text": ("#f59e0b", 6),
    "action": ("#16a34a", 9),
    "rule": ("#7c3aed", 10),
    "safety_topic": ("#9333ea", 8),
    "dataset": ("#475569", 9),
    "work_order": ("#64748b", 5),
    "elevator": ("#0f766e", 8),
    "place": ("#64748b", 6),
    "site_type": ("#64748b", 6),
    "organization": ("#64748b", 6),
    "manufacturer": ("#64748b", 6),
    "maintenance_unit": ("#64748b", 6),
    "fault_location": ("#0ea5e9", 7),
    "part_type": ("#14b8a6", 7),
    "source": ("#6b7280", 6),
}

RELATION_ZH = {
    "HAS_SYSTEM": "包含系统",
    "HAS_COMPONENT": "包含部件",
    "BELONGS_TO_SYSTEM": "属于系统",
    "PART_OF_SAFETY_CHAIN": "属于安全链",
    "LIKELY_AFFECTS": "可能影响",
    "HAS_ROOT_COMPONENT": "关联关键部件",
    "CAUSES_PHENOMENON": "导致现象",
    "RECOMMENDS_ACTION": "建议处置",
    "CHECKS_COMPONENT": "检查部件",
    "MITIGATES": "缓解/消除",
    "COVERS_SAFETY_TOPIC": "覆盖安全主题",
    "DEFINES_MAINTENANCE_SCOPE": "定义维保范围",
    "SUPPORTS_CATEGORY": "支撑故障类别",
    "REPORTED_ON": "报修对象",
    "LOCATED_AT": "位于",
    "HAS_SITE_TYPE": "使用场所",
    "MAINTAINED_BY": "维保单位",
    "MANUFACTURED_BY": "制造单位",
    "HANDLED_BY": "处置单位",
    "HAS_RAW_FAULT_TEXT": "原始故障文本",
    "HAS_FAULT_CATEGORY": "故障归类",
    "HAS_FAULT_PHENOMENON": "故障现象",
    "OBSERVED_PHENOMENON": "观测到现象",
    "HAS_FAULT_LOCATION": "故障位置",
    "MAPS_TO_SYSTEM": "映射到系统",
    "MAPS_TO_COMPONENT": "映射到部件",
    "CATEGORIZED_AS": "归类为",
    "HAS_AGGREGATE_CAUSE": "聚合故障原因",
    "HAS_REPLACED_PART_TYPE": "更换部件类型",
    "DERIVED_FROM": "来源于",
}

RELATION_COLORS = {
    "HAS_SYSTEM": "#2563eb",
    "HAS_COMPONENT": "#0891b2",
    "BELONGS_TO_SYSTEM": "#0891b2",
    "PART_OF_SAFETY_CHAIN": "#9333ea",
    "LIKELY_AFFECTS": "#dc2626",
    "HAS_ROOT_COMPONENT": "#dc2626",
    "CAUSES_PHENOMENON": "#ea580c",
    "RECOMMENDS_ACTION": "#16a34a",
    "CHECKS_COMPONENT": "#16a34a",
    "MITIGATES": "#16a34a",
    "COVERS_SAFETY_TOPIC": "#7c3aed",
    "DEFINES_MAINTENANCE_SCOPE": "#7c3aed",
    "SUPPORTS_CATEGORY": "#7c3aed",
    "REPORTED_ON": "#64748b",
    "LOCATED_AT": "#64748b",
    "HAS_SITE_TYPE": "#64748b",
    "MAINTAINED_BY": "#64748b",
    "MANUFACTURED_BY": "#64748b",
    "HANDLED_BY": "#64748b",
    "HAS_RAW_FAULT_TEXT": "#f59e0b",
    "HAS_FAULT_CATEGORY": "#dc2626",
    "HAS_FAULT_PHENOMENON": "#ea580c",
    "OBSERVED_PHENOMENON": "#ea580c",
    "HAS_FAULT_LOCATION": "#0ea5e9",
    "MAPS_TO_SYSTEM": "#0ea5e9",
    "MAPS_TO_COMPONENT": "#14b8a6",
    "CATEGORIZED_AS": "#dc2626",
    "HAS_AGGREGATE_CAUSE": "#f59e0b",
    "HAS_REPLACED_PART_TYPE": "#14b8a6",
    "DERIVED_FROM": "#6b7280",
}

WEB_SOURCES = [
    {
        "id": "web:samr_tsg_2023",
        "name": "市场监管总局关于 TSG T7001-2023 与 TSG T7008-2023 的解读",
        "url": "https://www.samr.gov.cn/xw/zj/art/2023/art_971676b200df4c529d1971911f5927a7.html",
        "note": "用于监管规则节点和自行检测/定期检验语义。",
    },
    {
        "id": "web:samr_gbt_7588_2020",
        "name": "市场监管总局 GB/T 7588.1-2020/GB/T 7588.2-2020 解读",
        "url": "https://www.samr.gov.cn/sps/sjdt/gzdt/art/2023/art_72c228af3bd144c584a682322159199d.html",
        "note": "用于制动器、上行超速、轿厢意外移动、安全回路和救援检修相关节点。",
    },
    {
        "id": "web:tsg_t5002_2017",
        "name": "TSG T5002-2017 电梯维护保养规则",
        "url": "https://www.haian.gov.cn/hascjgj/sgjf/content/a8589ce7-7138-4c77-ab35-104a47e910ed.html",
        "note": "用于半月、季度、半年、年度维保范围和处置动作语义。",
    },
    {
        "id": "web:hangzhou_96333_2020",
        "name": "杭州市 96333 电梯应急处置通报",
        "url": "https://www.hangzhou.gov.cn/art/2020/8/28/art_812262_55518767.html",
        "note": "用于困人、门系统、人为原因、外部原因等故障类别证据。",
    },
    {
        "id": "web:taian_96333_2017",
        "name": "泰安市 96333 电梯应急处置服务平台数据",
        "url": "http://scjgj.taian.gov.cn/art/2017/10/9/art_201048_8273969.html",
        "note": "用于维保救援、人员原因、停电、进水等处置语义。",
    },
    {
        "id": "web:rizhao_96333_2021",
        "name": "日照市 96333 电梯应急处置中心运行情况通报",
        "url": "http://www.rizhao.gov.cn/art/2022/1/25/art_39601_10297757.html",
        "note": "用于困人原因的门系统、外部原因和人为原因统计语义。",
    },
    {
        "id": "web:elevator_gnn_literature",
        "name": "Graph-based / GNN elevator fault diagnosis literature",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12788203/",
        "note": "用于后续把该 KG 接入 GNN 异常追溯的技术背景。",
    },
]


class ElevatorKG:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, str]] = {}
        self.edges: dict[tuple[str, str, str], dict[str, str]] = {}

    def add_node(self, node_id: str, kind: str, name: str | None = None, **attrs: Any) -> None:
        if not node_id:
            return
        color, size = KIND_STYLE.get(kind, ("#64748b", 6))
        record = {field: "" for field in NODE_FIELDS}
        record.update(
            {
                "id": node_id,
                "label": node_id,
                "name": normalize_space(name or node_id),
                "kind": kind,
                "kind_zh": KIND_ZH.get(kind, kind),
                "color": color,
                "size": str(size),
            }
        )
        for key, value in attrs.items():
            if key in record:
                record[key] = stringify(value)
        existing = self.nodes.get(node_id)
        if existing is None:
            self.nodes[node_id] = record
            return
        for key, value in record.items():
            if value and not existing.get(key):
                existing[key] = value
        if record.get("count"):
            existing["count"] = stringify(safe_int(existing.get("count")) + safe_int(record.get("count")))
        if record.get("weight"):
            existing["weight"] = stringify(max(safe_float(existing.get("weight")), safe_float(record.get("weight"))))

    def add_edge(
        self,
        source: str,
        relation: str,
        target: str,
        *,
        relation_zh: str | None = None,
        evidence: str = "",
        source_doc: str = "",
        source_url: str = "",
        count: int | str = 1,
        weight: float | str | None = None,
    ) -> None:
        if not source or not relation or not target:
            return
        key = (source, relation, target)
        record = {field: "" for field in EDGE_FIELDS}
        record.update(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "relation_zh": relation_zh or RELATION_ZH.get(relation, relation),
                "evidence": normalize_space(evidence),
                "source_doc": normalize_space(source_doc),
                "source_url": normalize_space(source_url),
                "count": stringify(count),
                "weight": stringify(weight if weight is not None else count),
                "color": RELATION_COLORS.get(relation, "#64748b"),
            }
        )
        existing = self.edges.get(key)
        if existing is None:
            self.edges[key] = record
            return
        existing["count"] = stringify(safe_int(existing.get("count")) + safe_int(record.get("count")))
        existing["weight"] = stringify(max(safe_float(existing.get("weight")), safe_float(record.get("weight"))))
        existing["evidence"] = merge_text(existing.get("evidence", ""), record.get("evidence", ""))
        existing["source_doc"] = merge_text(existing.get("source_doc", ""), record.get("source_doc", ""))
        existing["source_url"] = merge_text(existing.get("source_url", ""), record.get("source_url", ""))

    def node_records(self) -> list[dict[str, str]]:
        return [self.nodes[node_id] for node_id in sorted(self.nodes)]

    def edge_records(self) -> list[dict[str, str]]:
        return [
            self.edges[key]
            for key in sorted(self.edges, key=lambda item: (item[1], item[0], item[2]))
        ]

    def summary(self) -> dict[str, Any]:
        node_kinds = Counter(record["kind"] for record in self.nodes.values())
        relations = Counter(record["relation"] for record in self.edges.values())
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_kinds": dict(sorted(node_kinds.items())),
            "relations": dict(sorted(relations.items())),
        }


SYSTEMS = [
    ("system:traction", "曳引系统", "提供电梯运行牵引力，包含曳引机、曳引轮、钢丝绳、制动器等。"),
    ("system:guidance", "导向系统", "约束轿厢和对重沿导轨运行。"),
    ("system:door", "门系统", "实现厅门、轿门开闭、门锁闭合、防夹保护和门区联锁。"),
    ("system:car", "轿厢系统", "承载乘客并提供操纵、照明、通风和轿内安全功能。"),
    ("system:counterweight", "重量平衡系统", "通过对重和平衡补偿降低曳引负荷。"),
    ("system:electric_drive", "电力拖动系统", "实现电机驱动、变频调速和运行控制。"),
    ("system:electric_control", "电气控制系统", "处理召唤、运行逻辑、平层、通讯和故障保护。"),
    ("system:safety_protection", "安全保护系统", "由门锁、安全回路、限速器、安全钳、缓冲器、急停等构成。"),
    ("system:shaft_station", "井道与层站系统", "包含井道、层门、层站召唤、端站限位和井道位置检测。"),
    ("system:pit", "底坑系统", "包含缓冲器、底坑急停、张紧装置、积水环境等。"),
    ("system:power_environment", "供电与外部环境", "覆盖停电、电压异常、进水、温湿度和外部施工影响。"),
]

COMPONENTS = [
    ("component:traction_machine", "曳引机", "system:traction"),
    ("component:brake", "制动器/抱闸", "system:traction"),
    ("component:traction_rope", "曳引钢丝绳", "system:traction"),
    ("component:sheave", "曳引轮", "system:traction"),
    ("component:governor", "限速器", "system:safety_protection"),
    ("component:safety_gear", "安全钳", "system:safety_protection"),
    ("component:buffer", "缓冲器", "system:pit"),
    ("component:guide_rail", "导轨", "system:guidance"),
    ("component:counterweight", "对重", "system:counterweight"),
    ("component:car", "轿厢", "system:car"),
    ("component:car_operating_panel", "轿内操纵箱", "system:car"),
    ("component:call_button", "外呼/内选按钮", "system:electric_control"),
    ("component:landing_door", "厅门", "system:door"),
    ("component:car_door", "轿门", "system:door"),
    ("component:door_machine", "门机", "system:door"),
    ("component:landing_door_lock", "厅门锁/门锁触点", "system:door"),
    ("component:car_door_lock", "轿门锁", "system:door"),
    ("component:door_lock_circuit", "门锁回路", "system:safety_protection"),
    ("component:light_curtain", "光幕/防夹装置", "system:door"),
    ("component:door_sill", "地坎/门导轨", "system:door"),
    ("component:door_slider", "门滑块", "system:door"),
    ("component:controller", "控制柜/主板", "system:electric_control"),
    ("component:inverter", "变频器", "system:electric_drive"),
    ("component:contactor", "接触器", "system:electric_control"),
    ("component:encoder", "编码器", "system:electric_control"),
    ("component:leveling_sensor", "平层传感器", "system:electric_control"),
    ("component:limit_switch", "限位/减速开关", "system:safety_protection"),
    ("component:emergency_stop", "急停开关", "system:safety_protection"),
    ("component:safety_circuit", "安全回路", "system:safety_protection"),
    ("component:power_supply", "供电电源", "system:power_environment"),
    ("component:pit_water", "底坑积水/进水", "system:power_environment"),
]

PHENOMENA = [
    ("phenomenon:trap", "困人"),
    ("phenomenon:not_running", "不运行/停梯"),
    ("phenomenon:open_door_bad", "开门不良"),
    ("phenomenon:close_door_bad", "关门不良"),
    ("phenomenon:door_blocked", "开关门受阻"),
    ("phenomenon:emergency_stop", "急停"),
    ("phenomenon:leveling_bad", "平层不良"),
    ("phenomenon:safety_chain_open", "安全回路断开"),
    ("phenomenon:brake_fault", "制动器故障"),
    ("phenomenon:controller_crash", "控制系统死机"),
    ("phenomenon:water_shutdown", "进水停梯"),
    ("phenomenon:power_loss", "停电/电源异常"),
    ("phenomenon:abnormal_noise", "异响/抖动"),
]

ACTIONS = [
    ("action:rescue_release_passenger", "救援开门放人"),
    ("action:clean_sill", "清理地坎/门导轨"),
    ("action:adjust_door", "调整厅轿门/门机"),
    ("action:inspect_door_lock", "检查门锁触点/门锁回路"),
    ("action:replace_light_curtain", "更换或调整光幕"),
    ("action:reset_controller", "复位/重启控制系统"),
    ("action:inspect_safety_circuit", "检查安全回路"),
    ("action:inspect_brake", "检查制动器/抱闸"),
    ("action:inspect_leveling", "检查平层/位置检测"),
    ("action:drain_and_dry", "排水干燥"),
    ("action:restore_power", "恢复供电/检查电压相序"),
    ("action:replace_button_switch", "更换按钮/开关"),
    ("action:periodic_maintenance", "周期性维护保养"),
    ("action:user_education", "使用行为提示"),
]

SAFETY_TOPICS = [
    ("topic:electric_safety_chain", "电气安全链"),
    ("topic:brake_safety", "制动器安全"),
    ("topic:ascending_overspeed", "轿厢上行超速保护"),
    ("topic:unintended_car_movement", "轿厢意外移动保护"),
    ("topic:rescue_access", "救援和检修通道"),
    ("topic:door_locking", "门锁闭合与门区联锁"),
]

RULES = [
    ("rule:gbt_7588_2020", "GB/T 7588.1-2020 / GB/T 7588.2-2020", "电梯制造与安装安全规范。"),
    ("rule:tsg_t7001_2023", "TSG T7001-2023 电梯监督检验和定期检验规则", "电梯监督检验和定期检验规则。"),
    ("rule:tsg_t7008_2023", "TSG T7008-2023 电梯自行检测规则", "电梯自行检测规则。"),
    ("rule:tsg_t5002_2017", "TSG T5002-2017 电梯维护保养规则", "电梯维护保养规则。"),
    ("rule:96333_response", "96333 电梯应急处置/救援响应", "电梯困人应急处置、救援到场和回访闭环。"),
]

CATEGORY_INFO = [
    {
        "id": "category:human_obstruction",
        "name": "人为阻挡/垃圾卡阻",
        "keywords": ["生活垃圾", "垃圾", "挡门", "档门", "堵门", "阻挡", "卡住", "卡牢", "地坎", "门导轨有灰", "野蛮搬运", "异物"],
        "system": "system:door",
        "components": ["component:door_sill", "component:door_slider", "component:landing_door", "component:car_door"],
        "phenomena": ["phenomenon:door_blocked", "phenomenon:close_door_bad", "phenomenon:trap", "phenomenon:not_running"],
        "actions": ["action:clean_sill", "action:inspect_door_lock", "action:user_education"],
    },
    {
        "id": "category:door_system_fault",
        "name": "门系统故障",
        "keywords": ["门机", "厅门", "轿门", "门锁", "光幕", "安全触板", "门触点", "防夹", "开门", "关门", "门区"],
        "system": "system:door",
        "components": ["component:door_machine", "component:landing_door_lock", "component:car_door_lock", "component:light_curtain"],
        "phenomena": ["phenomenon:open_door_bad", "phenomenon:close_door_bad", "phenomenon:door_blocked", "phenomenon:trap"],
        "actions": ["action:adjust_door", "action:inspect_door_lock", "action:replace_light_curtain"],
    },
    {
        "id": "category:water_environment",
        "name": "进水/环境影响",
        "keywords": ["进水", "水浸", "底坑水", "漏水", "潮湿", "雨水", "风太大", "环境"],
        "system": "system:power_environment",
        "components": ["component:pit_water", "component:safety_circuit", "component:controller"],
        "phenomena": ["phenomenon:water_shutdown", "phenomenon:safety_chain_open", "phenomenon:not_running"],
        "actions": ["action:drain_and_dry", "action:inspect_safety_circuit"],
    },
    {
        "id": "category:power_supply",
        "name": "外部供电异常",
        "keywords": ["停电", "断电", "电源", "电压", "缺相", "相序", "跳闸", "供电"],
        "system": "system:power_environment",
        "components": ["component:power_supply", "component:controller", "component:contactor"],
        "phenomena": ["phenomenon:power_loss", "phenomenon:not_running", "phenomenon:trap"],
        "actions": ["action:restore_power", "action:reset_controller"],
    },
    {
        "id": "category:safety_chain_open",
        "name": "安全保护回路断开",
        "keywords": ["安全回路", "急停", "限位", "减速开关", "限速器", "安全钳", "保护动作", "自我保护"],
        "system": "system:safety_protection",
        "components": ["component:safety_circuit", "component:emergency_stop", "component:limit_switch", "component:governor"],
        "phenomena": ["phenomenon:safety_chain_open", "phenomenon:emergency_stop", "phenomenon:not_running"],
        "actions": ["action:inspect_safety_circuit", "action:inspect_door_lock"],
    },
    {
        "id": "category:brake_traction",
        "name": "制动/曳引异常",
        "keywords": ["制动", "抱闸", "曳引", "钢丝绳", "主机", "溜车", "冲顶", "蹲底"],
        "system": "system:traction",
        "components": ["component:brake", "component:traction_machine", "component:traction_rope", "component:governor"],
        "phenomena": ["phenomenon:brake_fault", "phenomenon:abnormal_noise", "phenomenon:not_running"],
        "actions": ["action:inspect_brake", "action:periodic_maintenance"],
    },
    {
        "id": "category:leveling_position",
        "name": "平层/位置检测异常",
        "keywords": ["平层", "编码器", "感应器", "位置", "楼层", "端站", "不到站", "冲层"],
        "system": "system:electric_control",
        "components": ["component:leveling_sensor", "component:encoder", "component:limit_switch"],
        "phenomena": ["phenomenon:leveling_bad", "phenomenon:not_running"],
        "actions": ["action:inspect_leveling", "action:inspect_safety_circuit"],
    },
    {
        "id": "category:control_system_fault",
        "name": "控制系统故障/死机",
        "keywords": ["死机", "重启", "控制", "主板", "通讯", "变频器", "接触器", "程序", "外呼板"],
        "system": "system:electric_control",
        "components": ["component:controller", "component:inverter", "component:contactor", "component:call_button"],
        "phenomena": ["phenomenon:controller_crash", "phenomenon:not_running"],
        "actions": ["action:reset_controller", "action:replace_button_switch"],
    },
    {
        "id": "category:maintenance_operation",
        "name": "维保/检修操作",
        "keywords": ["保养", "维保", "检修", "年检", "巡检", "测试"],
        "system": "system:electric_control",
        "components": ["component:controller", "component:safety_circuit"],
        "phenomena": ["phenomenon:not_running"],
        "actions": ["action:periodic_maintenance", "action:rescue_release_passenger"],
    },
    {
        "id": "category:false_duplicate_normal",
        "name": "误报/重复/到场正常",
        "keywords": ["误报", "重复", "到达正常", "电梯正常", "正常", "催促", "已配合"],
        "system": "system:electric_control",
        "components": ["component:controller"],
        "phenomena": ["phenomenon:not_running"],
        "actions": ["action:periodic_maintenance"],
    },
]

UNKNOWN_CATEGORY = {
    "id": "category:unknown",
    "name": "未归类故障",
    "keywords": [],
    "system": "system:electric_control",
    "components": ["component:controller"],
    "phenomena": ["phenomenon:not_running"],
    "actions": ["action:periodic_maintenance"],
}

PHENOMENON_KEYWORDS = [
    ("phenomenon:safety_chain_open", ["安全回路"]),
    ("phenomenon:brake_fault", ["制动器", "抱闸"]),
    ("phenomenon:open_door_bad", ["开门"]),
    ("phenomenon:close_door_bad", ["关门"]),
    ("phenomenon:door_blocked", ["挡门", "堵门", "卡门", "门卡", "开关门受阻"]),
    ("phenomenon:trap", ["困人", "关人"]),
    ("phenomenon:emergency_stop", ["急停"]),
    ("phenomenon:leveling_bad", ["平层"]),
    ("phenomenon:controller_crash", ["死机"]),
    ("phenomenon:water_shutdown", ["进水"]),
    ("phenomenon:power_loss", ["停电", "电源"]),
    ("phenomenon:not_running", ["不运行", "不动车", "停梯", "不动"]),
]

LOCATION_TO_SYSTEM = {
    "厅轿门系统": "system:door",
    "轿厢系统": "system:car",
    "底坑": "system:pit",
    "厅外部件": "system:shaft_station",
    "控制柜": "system:electric_control",
    "主机、限速器": "system:traction",
    "井道部件": "system:shaft_station",
    "其他": "system:power_environment",
}

PART_TO_COMPONENT_KEYWORDS = [
    ("component:call_button", ["按钮", "按键", "外呼板", "显示板"]),
    ("component:light_curtain", ["光幕", "安全触板"]),
    ("component:limit_switch", ["限位", "减速开关", "开关"]),
    ("component:door_slider", ["滑块"]),
    ("component:door_sill", ["地坎", "导轨"]),
    ("component:landing_door_lock", ["门锁", "触点"]),
    ("component:controller", ["主板", "控制板"]),
    ("component:brake", ["制动", "抱闸"]),
]


def build_domain_graph() -> ElevatorKG:
    graph = ElevatorKG()
    add_sources(graph)
    graph.add_node(
        "asset:elevator",
        "asset",
        "电梯",
        description="面向异常可解释性追溯的电梯整机知识图谱根节点。",
        source="领域种子图",
    )
    graph.add_node(
        "dataset:rescue_orders_2025",
        "dataset",
        "2025年200台电梯困人工单数据",
        description="本地困人工单数据，导出时仅使用非个人隐私字段。",
        source="local:2025年200台电梯困人工单数据.xlsx",
    )
    graph.add_node(
        "dataset:fau_rep",
        "dataset",
        "电梯故障报修数据 fau_rep",
        description="本地故障报修数据和故障原因计数表。",
        source="local:fau_rep.xls",
    )

    for system_id, name, description in SYSTEMS:
        graph.add_node(system_id, "system", name, description=description, source="领域种子图")
        graph.add_edge("asset:elevator", "HAS_SYSTEM", system_id, source_doc="领域种子图")

    for component_id, name, system_id in COMPONENTS:
        graph.add_node(component_id, "component", name, source="领域种子图")
        graph.add_edge(system_id, "HAS_COMPONENT", component_id, source_doc="领域种子图")
        graph.add_edge(component_id, "BELONGS_TO_SYSTEM", system_id, source_doc="领域种子图")

    for phenomenon_id, name in PHENOMENA:
        graph.add_node(phenomenon_id, "fault_phenomenon", name, source="领域种子图")

    for action_id, name in ACTIONS:
        graph.add_node(action_id, "action", name, source="领域种子图")

    for topic_id, name in SAFETY_TOPICS:
        graph.add_node(topic_id, "safety_topic", name, source="领域种子图")

    for rule_id, name, description in RULES:
        graph.add_node(rule_id, "rule", name, description=description, source="法规/标准资料")

    add_safety_edges(graph)
    add_category_edges(graph)
    add_rule_edges(graph)
    return graph


def add_sources(graph: ElevatorKG) -> None:
    for source in WEB_SOURCES:
        graph.add_node(
            source["id"],
            "source",
            source["name"],
            description=source["note"],
            source="web",
            source_url=source["url"],
        )


def add_safety_edges(graph: ElevatorKG) -> None:
    safety_chain_components = [
        "component:landing_door_lock",
        "component:car_door_lock",
        "component:door_lock_circuit",
        "component:safety_circuit",
        "component:emergency_stop",
        "component:limit_switch",
        "component:governor",
        "component:safety_gear",
        "component:buffer",
    ]
    for component_id in safety_chain_components:
        graph.add_edge(component_id, "PART_OF_SAFETY_CHAIN", "system:safety_protection", source_doc="领域种子图")

    graph.add_edge("component:brake", "PART_OF_SAFETY_CHAIN", "system:safety_protection", source_doc="GB/T 7588-2020")
    graph.add_edge("component:door_lock_circuit", "CHECKS_COMPONENT", "component:landing_door_lock", source_doc="领域种子图")
    graph.add_edge("component:door_lock_circuit", "CHECKS_COMPONENT", "component:car_door_lock", source_doc="领域种子图")


def add_category_edges(graph: ElevatorKG) -> None:
    for category in [*CATEGORY_INFO, UNKNOWN_CATEGORY]:
        category_id = category["id"]
        graph.add_node(category_id, "fault_category", category["name"], source="领域种子图")
        graph.add_edge(category_id, "LIKELY_AFFECTS", category["system"], source_doc="领域种子图")
        for component_id in category["components"]:
            graph.add_edge(category_id, "HAS_ROOT_COMPONENT", component_id, source_doc="领域种子图")
        for phenomenon_id in category["phenomena"]:
            graph.add_edge(category_id, "CAUSES_PHENOMENON", phenomenon_id, source_doc="领域种子图")
        for action_id in category["actions"]:
            graph.add_edge(category_id, "RECOMMENDS_ACTION", action_id, source_doc="领域种子图")

    mitigation = {
        "action:clean_sill": ["phenomenon:door_blocked", "phenomenon:close_door_bad"],
        "action:adjust_door": ["phenomenon:open_door_bad", "phenomenon:close_door_bad"],
        "action:inspect_door_lock": ["phenomenon:safety_chain_open", "phenomenon:trap"],
        "action:reset_controller": ["phenomenon:controller_crash", "phenomenon:not_running"],
        "action:drain_and_dry": ["phenomenon:water_shutdown", "phenomenon:safety_chain_open"],
        "action:restore_power": ["phenomenon:power_loss", "phenomenon:not_running"],
        "action:inspect_brake": ["phenomenon:brake_fault"],
        "action:inspect_leveling": ["phenomenon:leveling_bad"],
        "action:rescue_release_passenger": ["phenomenon:trap"],
    }
    for action_id, phenomena in mitigation.items():
        for phenomenon_id in phenomena:
            graph.add_edge(action_id, "MITIGATES", phenomenon_id, source_doc="领域种子图")


def add_rule_edges(graph: ElevatorKG) -> None:
    gbt_url = WEB_SOURCES[1]["url"]
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:electric_safety_chain", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:brake_safety", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:ascending_overspeed", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:unintended_car_movement", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:rescue_access", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)
    graph.add_edge("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:door_locking", source_doc=WEB_SOURCES[1]["name"], source_url=gbt_url)

    t700_url = WEB_SOURCES[0]["url"]
    graph.add_edge("rule:tsg_t7001_2023", "COVERS_SAFETY_TOPIC", "topic:electric_safety_chain", source_doc=WEB_SOURCES[0]["name"], source_url=t700_url)
    graph.add_edge("rule:tsg_t7008_2023", "COVERS_SAFETY_TOPIC", "topic:electric_safety_chain", source_doc=WEB_SOURCES[0]["name"], source_url=t700_url)
    graph.add_edge("rule:tsg_t7001_2023", "SUPPORTS_CATEGORY", "category:safety_chain_open", source_doc=WEB_SOURCES[0]["name"], source_url=t700_url)
    graph.add_edge("rule:tsg_t7008_2023", "SUPPORTS_CATEGORY", "category:door_system_fault", source_doc=WEB_SOURCES[0]["name"], source_url=t700_url)

    t5002_url = WEB_SOURCES[2]["url"]
    graph.add_edge("rule:tsg_t5002_2017", "DEFINES_MAINTENANCE_SCOPE", "action:periodic_maintenance", source_doc=WEB_SOURCES[2]["name"], source_url=t5002_url)
    graph.add_edge("rule:tsg_t5002_2017", "SUPPORTS_CATEGORY", "category:door_system_fault", source_doc=WEB_SOURCES[2]["name"], source_url=t5002_url)
    graph.add_edge("rule:tsg_t5002_2017", "SUPPORTS_CATEGORY", "category:brake_traction", source_doc=WEB_SOURCES[2]["name"], source_url=t5002_url)

    for source in WEB_SOURCES[3:6]:
        graph.add_edge("rule:96333_response", "SUPPORTS_CATEGORY", "category:door_system_fault", source_doc=source["name"], source_url=source["url"])
        graph.add_edge("rule:96333_response", "SUPPORTS_CATEGORY", "category:human_obstruction", source_doc=source["name"], source_url=source["url"])
        graph.add_edge("rule:96333_response", "SUPPORTS_CATEGORY", "category:power_supply", source_doc=source["name"], source_url=source["url"])
        graph.add_edge("rule:96333_response", "SUPPORTS_CATEGORY", "category:water_environment", source_doc=source["name"], source_url=source["url"])


def classify_fault_text(text: Any) -> dict[str, Any]:
    normalized = normalize_space(text)
    matched = UNKNOWN_CATEGORY
    for category in CATEGORY_INFO:
        if any(keyword in normalized for keyword in category["keywords"]):
            matched = category
            break
    system_name = node_name_by_id(matched["system"])
    component_names = [node_name_by_id(component_id) for component_id in matched["components"]]
    phenomenon_names = [node_name_by_id(phenomenon_id) for phenomenon_id in matched["phenomena"]]
    action_names = [node_name_by_id(action_id) for action_id in matched["actions"]]
    return {
        "text": normalized,
        "category": matched["name"],
        "category_id": matched["id"],
        "system": system_name,
        "system_id": matched["system"],
        "components": component_names,
        "component_ids": matched["components"],
        "phenomena": phenomenon_names,
        "phenomenon_ids": matched["phenomena"],
        "actions": action_names,
        "action_ids": matched["actions"],
    }


def add_rescue_order_records(graph: ElevatorKG, records: Any) -> None:
    for _, row in records.iterrows():
        order_no = normalize_space(row.get("工单编号"))
        if not order_no:
            continue
        order_id = f"work_order:{order_no}"
        trapped_people = normalize_space(row.get("困人数"))
        rescue_minutes = normalize_space(row.get("救援用时"))
        graph.add_node(
            order_id,
            "work_order",
            f"工单 {order_no}",
            source="local:2025年200台电梯困人工单数据.xlsx",
            trapped_people=trapped_people,
            rescue_minutes=rescue_minutes,
        )
        graph.add_edge(order_id, "DERIVED_FROM", "dataset:rescue_orders_2025", source_doc="local:xlsx")

        elevator_code = normalize_space(row.get("注册代码"))
        if elevator_code:
            elevator_id = f"elevator:{elevator_code}"
            graph.add_node(elevator_id, "elevator", f"电梯 {elevator_code}", source="local:xlsx")
            graph.add_edge(order_id, "REPORTED_ON", elevator_id, source_doc="local:xlsx")

            maintenance = normalize_space(row.get("维保单位"))
            if maintenance:
                maintenance_id = f"maintenance_unit:{maintenance}"
                graph.add_node(maintenance_id, "maintenance_unit", maintenance, source="local:xlsx")
                graph.add_edge(elevator_id, "MAINTAINED_BY", maintenance_id, source_doc="local:xlsx")
                graph.add_edge(order_id, "HANDLED_BY", maintenance_id, source_doc="local:xlsx")

            manufacturer = normalize_space(row.get("制造单位"))
            if manufacturer:
                manufacturer_id = f"manufacturer:{manufacturer}"
                graph.add_node(manufacturer_id, "manufacturer", manufacturer, source="local:xlsx")
                graph.add_edge(elevator_id, "MANUFACTURED_BY", manufacturer_id, source_doc="local:xlsx")

            address = normalize_space(row.get("电梯地址"))
            if address:
                place_id = text_node_id("place", address, limit=80)
                graph.add_node(place_id, "place", address, source="local:xlsx")
                graph.add_edge(elevator_id, "LOCATED_AT", place_id, source_doc="local:xlsx")
                graph.add_edge(order_id, "LOCATED_AT", place_id, source_doc="local:xlsx")

            site_type = normalize_space(row.get("使用场所"))
            if site_type:
                site_id = f"site_type:{site_type}"
                graph.add_node(site_id, "site_type", site_type, source="local:xlsx")
                graph.add_edge(elevator_id, "HAS_SITE_TYPE", site_id, source_doc="local:xlsx")

        cause_text = normalize_space(row.get("故障原因"))
        if cause_text:
            cause_id = text_node_id("raw_cause", cause_text, limit=100)
            graph.add_node(cause_id, "raw_fault_text", cause_text, source="local:xlsx", count=1)
            graph.add_edge(order_id, "HAS_RAW_FAULT_TEXT", cause_id, source_doc="local:xlsx")
            classification = classify_fault_text(cause_text)
            graph.add_edge(order_id, "HAS_FAULT_CATEGORY", classification["category_id"], evidence=cause_text, source_doc="local:xlsx")
            graph.add_edge(cause_id, "CATEGORIZED_AS", classification["category_id"], evidence=cause_text, source_doc="local:xlsx")
            for phenomenon_id in classification["phenomenon_ids"]:
                graph.add_edge(order_id, "HAS_FAULT_PHENOMENON", phenomenon_id, evidence=cause_text, source_doc="local:xlsx")


def add_fault_report_aggregates(graph: ElevatorKG, fau_records: Any, cause_counts: Any, *, top_n_causes: int = 500) -> None:
    graph.add_edge("dataset:fau_rep", "DERIVED_FROM", "web:elevator_gnn_literature", source_doc="KG-GNN 技术背景")
    add_cause_count_edges(graph, cause_counts, top_n_causes=top_n_causes)
    add_value_count_edges(graph, fau_records, "FAU_PHENOMENON", "fault_phenomenon", "OBSERVED_PHENOMENON", top_n=120)
    add_fault_location_edges(graph, fau_records, top_n=80)
    add_part_type_edges(graph, fau_records, top_n=120)


def add_cause_count_edges(graph: ElevatorKG, cause_counts: Any, *, top_n_causes: int) -> None:
    if cause_counts is None or cause_counts.empty:
        return
    cause_col = cause_counts.columns[0]
    count_col = cause_counts.columns[1] if len(cause_counts.columns) > 1 else None
    ratio_col = cause_counts.columns[2] if len(cause_counts.columns) > 2 else None
    for _, row in cause_counts.head(top_n_causes).iterrows():
        text = normalize_space(row.get(cause_col))
        if not text:
            continue
        count = safe_int(row.get(count_col)) if count_col else 1
        ratio = safe_float(row.get(ratio_col)) if ratio_col else count
        cause_id = text_node_id("raw_cause", text, limit=100)
        graph.add_node(cause_id, "raw_fault_text", text, source="local:fau_rep.xls", count=count, weight=ratio)
        graph.add_edge("dataset:fau_rep", "HAS_AGGREGATE_CAUSE", cause_id, evidence=text, source_doc="local:fau_rep.xls", count=count, weight=ratio)
        classification = classify_fault_text(text)
        graph.add_edge(cause_id, "CATEGORIZED_AS", classification["category_id"], evidence=text, source_doc="local:fau_rep.xls", count=count, weight=ratio)


def add_value_count_edges(graph: ElevatorKG, records: Any, column: str, kind: str, relation: str, *, top_n: int) -> None:
    if records is None or column not in records.columns:
        return
    values = clean_series(records[column])
    for text, count in values.value_counts().head(top_n).items():
        canonical = canonical_phenomenon_id(text) if kind == "fault_phenomenon" else None
        node_id = canonical or text_node_id(kind, text, limit=80)
        name = node_name_by_id(node_id) if canonical else text
        graph.add_node(node_id, kind, name, source="local:fau_rep.xls", count=int(count))
        graph.add_edge("dataset:fau_rep", relation, node_id, evidence=text, source_doc="local:fau_rep.xls", count=int(count), weight=int(count))


def add_fault_location_edges(graph: ElevatorKG, records: Any, *, top_n: int) -> None:
    if records is None or "FAU_LOC" not in records.columns:
        return
    values = clean_series(records["FAU_LOC"])
    for text, count in values.value_counts().head(top_n).items():
        location_id = f"fault_location:{text}"
        graph.add_node(location_id, "fault_location", text, source="local:fau_rep.xls", count=int(count))
        graph.add_edge("dataset:fau_rep", "HAS_FAULT_LOCATION", location_id, source_doc="local:fau_rep.xls", count=int(count), weight=int(count))
        system_id = LOCATION_TO_SYSTEM.get(text)
        if system_id:
            graph.add_edge(location_id, "MAPS_TO_SYSTEM", system_id, source_doc="local:fau_rep.xls", count=int(count), weight=int(count))


def add_part_type_edges(graph: ElevatorKG, records: Any, *, top_n: int) -> None:
    if records is None or "PART_TYPE" not in records.columns:
        return
    values = clean_series(records["PART_TYPE"])
    for text, count in values.value_counts().head(top_n).items():
        part_id = text_node_id("part_type", text, limit=80)
        graph.add_node(part_id, "part_type", text, source="local:fau_rep.xls", count=int(count))
        graph.add_edge("dataset:fau_rep", "HAS_REPLACED_PART_TYPE", part_id, source_doc="local:fau_rep.xls", count=int(count), weight=int(count))
        component_id = map_part_to_component(text)
        if component_id:
            graph.add_edge(part_id, "MAPS_TO_COMPONENT", component_id, source_doc="local:fau_rep.xls", count=int(count), weight=int(count))


def load_local_frames(data_dir: Path = BASE_DIR) -> tuple[Any, Any, Any]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("需要 pandas 才能读取本地 Excel 数据。") from exc
    xlsx_files = sorted(data_dir.glob("*.xlsx"))
    xls_files = sorted(path for path in data_dir.glob("*.xls") if path.name != "~$fau_rep.xls")
    if not xlsx_files:
        raise FileNotFoundError(f"未在 {data_dir} 找到 .xlsx 工单数据。")
    if not xls_files:
        raise FileNotFoundError(f"未在 {data_dir} 找到 .xls 故障报修数据。")
    rescue_orders = pd.read_excel(xlsx_files[0], sheet_name=0)
    fau_records = pd.read_excel(xls_files[0], sheet_name=0, engine="xlrd")
    cause_counts = pd.read_excel(xls_files[0], sheet_name=1, engine="xlrd")
    return rescue_orders, fau_records, cause_counts


def export_elevator_kg(output_dir: str | Path = BASE_DIR, *, include_local_data: bool = True, data_dir: str | Path | None = None) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    graph = build_domain_graph()

    if include_local_data:
        rescue_orders, fau_records, cause_counts = load_local_frames(Path(data_dir) if data_dir else BASE_DIR)
        add_rescue_order_records(graph, rescue_orders)
        add_fault_report_aggregates(graph, fau_records, cause_counts)

    files = {
        "nodes_csv": output / "elevator_kg_nodes.csv",
        "edges_csv": output / "elevator_kg_edges.csv",
        "neo4j_cypher": output / "neo4j_import.cypher",
        "json": output / "elevator_kg.json",
        "summary": output / "elevator_kg_summary.json",
        "schema": output / "elevator_kg_schema.md",
        "sources": output / "elevator_kg_sources.md",
        "readme": output / "README.md",
    }
    write_csv(files["nodes_csv"], graph.node_records(), NODE_FIELDS)
    write_csv(files["edges_csv"], graph.edge_records(), EDGE_FIELDS)
    files["neo4j_cypher"].write_text(export_neo4j_import_cypher_text({edge["relation"] for edge in graph.edge_records()}), encoding="utf-8")
    files["json"].write_text(json.dumps({"nodes": graph.node_records(), "edges": graph.edge_records()}, ensure_ascii=False, indent=2), encoding="utf-8")
    files["summary"].write_text(json.dumps(graph.summary(), ensure_ascii=False, indent=2), encoding="utf-8")
    files["schema"].write_text(export_schema_markdown(graph), encoding="utf-8")
    files["sources"].write_text(export_sources_markdown(), encoding="utf-8")
    files["readme"].write_text(export_readme_markdown(), encoding="utf-8")
    return files


def export_neo4j_import_cypher_text(relations: set[str]) -> str:
    lines = [
        "// Elevator KG Neo4j import script. Put elevator_kg_nodes.csv and elevator_kg_edges.csv in Neo4j's import directory.",
        "CREATE CONSTRAINT elevator_kg_node_id IF NOT EXISTS FOR (n:ElevatorKG) REQUIRE n.id IS UNIQUE;",
        "",
        "LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_nodes.csv' AS row",
        "MERGE (n:ElevatorKG {id: row.id})",
        "SET n.label = row.label,",
        "    n.name = row.name,",
        "    n.name_en = row.name_en,",
        "    n.kind = row.kind,",
        "    n.kind_zh = row.kind_zh,",
        "    n.description = row.description,",
        "    n.source = row.source,",
        "    n.source_url = row.source_url,",
        "    n.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,",
        "    n.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,",
        "    n.trapped_people = row.trapped_people,",
        "    n.rescue_minutes = row.rescue_minutes,",
        "    n.color = row.color,",
        "    n.size = CASE row.size WHEN '' THEN null ELSE toInteger(row.size) END;",
        "",
    ]
    for relation in sorted(relations):
        safe_relation = sanitize_relation_type(relation)
        lines.extend(
            [
                f"// {relation}",
                "LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row",
                f"WITH row WHERE row.relation = '{relation}'",
                "MATCH (s:ElevatorKG {id: row.source})",
                "MATCH (t:ElevatorKG {id: row.target})",
                f"MERGE (s)-[r:{safe_relation}]->(t)",
                "SET r.name = row.relation_zh,",
                "    r.relation = row.relation,",
                "    r.evidence = row.evidence,",
                "    r.source_doc = row.source_doc,",
                "    r.source_url = row.source_url,",
                "    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,",
                "    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,",
                "    r.color = row.color;",
                "",
            ]
        )
    lines.extend(
        [
            "// Example queries:",
            "// MATCH p=(:ElevatorKG {name:'困人'})<-[:CAUSES_PHENOMENON]-(:ElevatorKG)-[:LIKELY_AFFECTS|HAS_ROOT_COMPONENT]->() RETURN p LIMIT 50;",
            "// MATCH p=(:ElevatorKG {name:'门系统'})--() RETURN p LIMIT 100;",
            "// MATCH (c:ElevatorKG {kind:'fault_category'})<-[r:HAS_FAULT_CATEGORY]-(:ElevatorKG {kind:'work_order'}) RETURN c.name, count(r) AS n ORDER BY n DESC;",
        ]
    )
    return "\n".join(lines)


def export_schema_markdown(graph: ElevatorKG) -> str:
    summary = graph.summary()
    node_rows = "\n".join(f"| `{kind}` | {count} | {KIND_ZH.get(kind, kind)} |" for kind, count in summary["node_kinds"].items())
    rel_rows = "\n".join(f"| `{rel}` | {count} | {RELATION_ZH.get(rel, rel)} |" for rel, count in summary["relations"].items())
    return f"""# Elevator KG Schema

## Node Kinds

| kind | count | 中文 |
|---|---:|---|
{node_rows}

## Relationship Types

| relation | count | 中文 |
|---|---:|---|
{rel_rows}

## Traceability Path Examples

- `work_order -> HAS_FAULT_CATEGORY -> fault_category -> LIKELY_AFFECTS -> system`
- `work_order -> HAS_RAW_FAULT_TEXT -> raw_fault_text -> CATEGORIZED_AS -> fault_category`
- `fault_category -> HAS_ROOT_COMPONENT -> component -> BELONGS_TO_SYSTEM -> system`
- `fault_category -> CAUSES_PHENOMENON -> fault_phenomenon`
- `fault_category -> RECOMMENDS_ACTION -> action`
- `rule/source -> SUPPORTS_CATEGORY/COVERS_SAFETY_TOPIC -> category/topic`
"""


def export_sources_markdown() -> str:
    lines = [
        "# Elevator KG Sources",
        "",
        "## Local Data",
        "",
        "- `2025年200台电梯困人工单数据.xlsx`: used only for work-order id, elevator registration code, place/site type, maintenance unit, manufacturer, fault reason, trapped-person count, rescue level, and rescue time. Personal names and phone numbers are not exported.",
        "- `fau_rep.xls`: used for aggregate fault phenomenon, fault cause, fault location, replacement-part type, trapped-person and source statistics.",
        "",
        "## Web References",
        "",
    ]
    for source in WEB_SOURCES:
        lines.append(f"- [{source['name']}]({source['url']}): {source['note']}")
    lines.append("")
    lines.append("The web references provide domain priors; local Excel data provides observed evidence and edge weights.")
    return "\n".join(lines)


def export_readme_markdown() -> str:
    return """# 电梯故障知识图谱

本目录包含面向电梯异常可解释性追溯的 Neo4j 可导入知识图谱。

## 文件

- `elevator_kg_builder.py`: 构建和导出脚本。
- `elevator_kg_nodes.csv`: 节点文件，`name` 已使用中文显示名。
- `elevator_kg_edges.csv`: 关系文件，包含中文关系名、证据、来源和权重。
- `neo4j_import.cypher`: Neo4j 导入脚本。
- `elevator_kg.json`: 节点/关系 JSON。
- `elevator_kg_summary.json`: 图谱规模统计。
- `elevator_kg_schema.md`: 节点类型、关系类型和追溯路径说明。
- `elevator_kg_sources.md`: 本地数据和网页资料来源。

## 重新生成

```powershell
python elevator_kg_builder.py --output-dir .
```

## Neo4j 导入

如果使用 Docker：

```powershell
docker run --name neo4j-elevator -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/password `
  -v E:/model/Root_kgd/elevator_KG:/var/lib/neo4j/import `
  neo4j:5
```

打开 Neo4j Browser 后执行 `neo4j_import.cypher` 的内容。

常用查询：

```cypher
MATCH p=(:ElevatorKG {name:'困人'})<-[:CAUSES_PHENOMENON]-(:ElevatorKG)-[:LIKELY_AFFECTS|HAS_ROOT_COMPONENT]->()
RETURN p LIMIT 50;

MATCH p=(:ElevatorKG {name:'门系统'})--()
RETURN p LIMIT 100;

MATCH (c:ElevatorKG {kind:'fault_category'})<-[r:HAS_FAULT_CATEGORY]-(:ElevatorKG {kind:'work_order'})
RETURN c.name AS 故障类别, count(r) AS 工单数
ORDER BY 工单数 DESC;
```
"""


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_series(series: Any) -> Any:
    values = series.dropna().astype(str).map(normalize_space)
    return values[values != ""]


def canonical_phenomenon_id(text: str) -> str | None:
    normalized = normalize_space(text)
    for phenomenon_id, keywords in PHENOMENON_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return phenomenon_id
    return None


def map_part_to_component(text: str) -> str | None:
    normalized = normalize_space(text)
    for component_id, keywords in PART_TO_COMPONENT_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return component_id
    return None


def node_name_by_id(node_id: str) -> str:
    for entries in (SYSTEMS, COMPONENTS, PHENOMENA, ACTIONS, SAFETY_TOPICS, RULES):
        for item in entries:
            if item[0] == node_id:
                return item[1]
    for category in [*CATEGORY_INFO, UNKNOWN_CATEGORY]:
        if category["id"] == node_id:
            return category["name"]
    return node_id


def text_node_id(prefix: str, text: str, *, limit: int) -> str:
    normalized = normalize_space(text)
    safe = re.sub(r"[\r\n\t]+", " ", normalized).strip()
    safe = safe[:limit]
    return f"{prefix}:{safe}"


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(value)).strip()


def stringify(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except Exception:
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def safe_int(value: Any) -> int:
    text = normalize_space(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def safe_float(value: Any) -> float:
    text = normalize_space(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def merge_text(left: str, right: str, *, limit: int = 500) -> str:
    parts = []
    for text in (left, right):
        text = normalize_space(text)
        if text and text not in parts:
            parts.append(text)
    merged = " | ".join(parts)
    return merged[:limit]


def sanitize_relation_type(relation: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", relation.upper())
    return sanitized or "RELATED_TO"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and export the elevator fault knowledge graph.")
    parser.add_argument("--output-dir", default=str(BASE_DIR), help="Directory for CSV/Cypher/JSON/Markdown outputs.")
    parser.add_argument("--data-dir", default=str(BASE_DIR), help="Directory containing the local xlsx/xls source files.")
    parser.add_argument("--domain-only", action="store_true", help="Export only the domain seed graph without local Excel data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    files = export_elevator_kg(
        args.output_dir,
        include_local_data=not args.domain_only,
        data_dir=args.data_dir,
    )
    for label, path in files.items():
        print(f"{label}: {path.resolve()}")


if __name__ == "__main__":
    main()
