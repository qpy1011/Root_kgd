from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "elevator_KG" / "elevator_kg_builder.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("elevator_kg_builder", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_fault_text_classification_maps_local_door_obstruction_case() -> None:
    builder = load_builder()

    result = builder.classify_fault_text("生活垃圾导致开关门受阻，电梯停止运行")

    assert result["category"] == "人为阻挡/垃圾卡阻"
    assert result["system"] == "门系统"
    assert "开关门受阻" in result["phenomena"]
    assert "清理地坎/门导轨" in result["actions"]


def test_domain_graph_contains_traceable_safety_and_rule_edges() -> None:
    builder = load_builder()
    graph = builder.build_domain_graph()

    edge_keys = {(edge["source"], edge["relation"], edge["target"]) for edge in graph.edge_records()}

    assert ("system:door", "HAS_COMPONENT", "component:landing_door_lock") in edge_keys
    assert ("component:landing_door_lock", "PART_OF_SAFETY_CHAIN", "system:safety_protection") in edge_keys
    assert ("category:door_system_fault", "LIKELY_AFFECTS", "system:door") in edge_keys
    assert ("rule:gbt_7588_2020", "COVERS_SAFETY_TOPIC", "topic:electric_safety_chain") in edge_keys
    assert ("rule:tsg_t5002_2017", "DEFINES_MAINTENANCE_SCOPE", "action:periodic_maintenance") in edge_keys


def test_rescue_order_records_add_privacy_preserving_traceability_edges() -> None:
    builder = load_builder()
    graph = builder.build_domain_graph()
    records = pd.DataFrame(
        [
            {
                "工单编号": "JS_TEST_001",
                "注册代码": "311TEST",
                "使用场所": "医院",
                "电梯地址": "测试地址1号",
                "使用单位": "测试使用单位",
                "维保单位": "测试维保单位",
                "制造单位": "测试制造单位",
                "故障原因": "生活垃圾导致开关门受阻，电梯停止运行",
                "困人数": 2,
                "救援级别": "维保单位救援",
                "救援用时": 12,
            }
        ]
    )

    builder.add_rescue_order_records(graph, records)

    nodes = {node["id"]: node for node in graph.node_records()}
    edge_keys = {(edge["source"], edge["relation"], edge["target"]) for edge in graph.edge_records()}

    assert nodes["work_order:JS_TEST_001"]["kind"] == "work_order"
    assert nodes["work_order:JS_TEST_001"]["trapped_people"] == "2"
    assert "求救电话" not in nodes["work_order:JS_TEST_001"]
    assert ("work_order:JS_TEST_001", "REPORTED_ON", "elevator:311TEST") in edge_keys
    assert ("work_order:JS_TEST_001", "HAS_FAULT_CATEGORY", "category:human_obstruction") in edge_keys
    assert ("elevator:311TEST", "MAINTAINED_BY", "maintenance_unit:测试维保单位") in edge_keys


def test_export_writes_neo4j_ready_csv_and_cypher(tmp_path: Path) -> None:
    builder = load_builder()

    files = builder.export_elevator_kg(tmp_path, include_local_data=False)

    assert files["nodes_csv"].name == "elevator_kg_nodes.csv"
    assert files["edges_csv"].name == "elevator_kg_edges.csv"
    assert files["neo4j_cypher"].name == "neo4j_import.cypher"

    with files["nodes_csv"].open(encoding="utf-8-sig", newline="") as handle:
        node_rows = list(csv.DictReader(handle))
    with files["edges_csv"].open(encoding="utf-8-sig", newline="") as handle:
        edge_rows = list(csv.DictReader(handle))
    cypher = files["neo4j_cypher"].read_text(encoding="utf-8")

    assert {"id", "name", "kind", "kind_zh", "description", "source", "count", "weight"}.issubset(
        node_rows[0].keys()
    )
    assert {"source", "target", "relation", "relation_zh", "evidence", "source_doc", "count", "weight"}.issubset(
        edge_rows[0].keys()
    )
    assert any(row["id"] == "system:door" and row["name"] == "门系统" for row in node_rows)
    assert any(row["relation"] == "HAS_COMPONENT" for row in edge_rows)
    assert "file:///elevator_kg_nodes.csv" in cypher
    assert "file:///elevator_kg_edges.csv" in cypher
    assert "r.name = row.relation_zh" in cypher
