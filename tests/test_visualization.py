from rootkgd.graph import KnowledgeGraph
from rootkgd.visualization import (
    edge_records,
    export_graphml_text,
    export_html_text,
    export_neo4j_import_cypher_text,
    node_label_zh,
    node_records,
)


def test_node_records_include_styling_fields() -> None:
    graph = KnowledgeGraph()
    graph.add_node("x1", "variable")
    graph.add_node("Reactor", "device")
    graph.add_edge("Reactor", "State", "x1")

    records = node_records(graph)

    assert records[0].keys() == {"id", "label", "name_zh", "kind", "kind_zh", "color", "size"}
    assert {record["kind"] for record in records} == {"variable", "device"}
    assert records[0]["name_zh"] == "x1 A进料（流股1）"


def test_edge_records_include_relation_styling_fields() -> None:
    graph = KnowledgeGraph()
    graph.add_node("Reactor", "device")
    graph.add_node("x1", "variable")
    graph.add_edge("Reactor", "State", "x1")

    records = edge_records(graph)

    assert records == [
        {
            "source": "Reactor",
            "target": "x1",
            "relation": "State",
            "relation_zh": "状态",
            "color": "#64748b",
        }
    ]


def test_export_graphml_text_contains_nodes_edges_and_relation_data() -> None:
    graph = KnowledgeGraph()
    graph.add_node("Reactor", "device")
    graph.add_node("x1", "variable")
    graph.add_edge("Reactor", "State", "x1")

    graphml = export_graphml_text(graph)

    assert "<graphml" in graphml
    assert 'id="Reactor"' in graphml
    assert "<data key=\"relation\">State</data>" in graphml
    assert "<data key=\"name_zh\">反应器</data>" in graphml


def test_export_neo4j_import_cypher_maps_relation_types() -> None:
    cypher = export_neo4j_import_cypher_text()

    assert "tep_pikg_nodes.csv" in cypher
    assert "tep_pikg_edges.csv" in cypher
    assert "n.name = row.name_zh" in cypher
    assert "r.name = row.relation_zh" in cypher
    assert ":STATE_OF" in cypher
    assert ":CONTAINED_BY" in cypher


def test_node_label_zh_handles_realistic_tep_utility_entities() -> None:
    assert node_label_zh("Stripper Steam", "stream") == "汽提蒸汽"
    assert node_label_zh("Cooling Water", "substance") == "冷却水"
    assert node_label_zh("Steam", "substance") == "蒸汽"


def test_export_html_text_uses_chinese_interface_labels() -> None:
    graph = KnowledgeGraph()
    graph.add_node("Reactor", "device")
    graph.add_node("x1", "variable")
    graph.add_edge("Reactor", "State", "x1")

    html = export_html_text(graph)

    assert '<html lang="zh-CN">' in html
    assert "TEP PIKG 可视化" in html
    assert "个节点" in html
    assert "条关系" in html
    assert '"variable": "变量"' in html
    assert '"State": "状态"' in html
