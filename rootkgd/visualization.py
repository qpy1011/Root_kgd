from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from xml.sax.saxutils import escape

from .graph import KnowledgeGraph
from .tep import build_tep_graph


KIND_STYLE = {
    "variable": {"color": "#2563eb", "size": 5},
    "stream": {"color": "#059669", "size": 8},
    "device": {"color": "#dc2626", "size": 12},
    "substance": {"color": "#d97706", "size": 7},
    "physical": {"color": "#64748b", "size": 8},
}

RELATION_COLORS = {
    "State": "#64748b",
    "State of": "#64748b",
    "Output": "#059669",
    "Contain": "#d97706",
    "Contained by": "#d97706",
    "Generate": "#7c3aed",
}

KIND_LABELS_ZH = {
    "variable": "变量",
    "stream": "流股",
    "device": "设备",
    "substance": "物质",
    "physical": "物理实体",
}

RELATION_LABELS_ZH = {
    "State": "状态",
    "State of": "状态所属",
    "Output": "输出",
    "Contain": "包含",
    "Contained by": "被包含",
    "Generate": "生成",
}

DEVICE_LABELS_ZH = {
    "Reactor": "反应器",
    "Separator": "产品分离器",
    "Stripper": "汽提塔",
    "Condenser": "冷凝器",
    "Compressor": "压缩机",
}

STREAM_LABELS_ZH = {
    "Stripper Steam": "汽提蒸汽",
}

SUBSTANCE_LABELS_ZH = {
    "Cooling Water": "冷却水",
    "Steam": "蒸汽",
}

VARIABLE_LABELS_ZH = {
    "x1": "A进料（流股1）",
    "x2": "D进料（流股2）",
    "x3": "E进料（流股3）",
    "x4": "A/C进料（流股4）",
    "x5": "循环流量（流股8）",
    "x6": "反应器进料流量（流股6）",
    "x7": "反应器压力",
    "x8": "反应器液位",
    "x9": "反应器温度",
    "x10": "排放流量（流股9）",
    "x11": "产品分离器温度",
    "x12": "产品分离器液位",
    "x13": "产品分离器压力",
    "x14": "产品分离器底流（流股10）",
    "x15": "汽提塔液位",
    "x16": "汽提塔压力",
    "x17": "汽提塔底流（流股11）",
    "x18": "汽提塔温度",
    "x19": "汽提塔蒸汽流量",
    "x20": "压缩机功率",
    "x21": "反应器冷却水出口温度",
    "x22": "分离器冷却水出口温度",
    "x23": "反应器进料组分A（流股6）",
    "x24": "反应器进料组分B（流股6）",
    "x25": "反应器进料组分C（流股6）",
    "x26": "反应器进料组分D（流股6）",
    "x27": "反应器进料组分E（流股6）",
    "x28": "反应器进料组分F（流股6）",
    "x29": "排放气组分A（流股9）",
    "x30": "排放气组分B（流股9）",
    "x31": "排放气组分C（流股9）",
    "x32": "排放气组分D（流股9）",
    "x33": "排放气组分E（流股9）",
    "x34": "排放气组分F（流股9）",
    "x35": "排放气组分G（流股9）",
    "x36": "排放气组分H（流股9）",
    "x37": "产品组分D（流股11）",
    "x38": "产品组分E（流股11）",
    "x39": "产品组分F（流股11）",
    "x40": "产品组分G（流股11）",
    "x41": "产品组分H（流股11）",
    "x42": "D进料流量（流股2）",
    "x43": "E进料流量（流股3）",
    "x44": "A进料流量（流股1）",
    "x45": "A/C进料流量（流股4）",
    "x46": "压缩机循环阀",
    "x47": "排放阀（流股9）",
    "x48": "分离器液体流量（流股10）",
    "x49": "汽提塔产品流量（流股11）",
    "x50": "汽提塔蒸汽阀",
    "x51": "反应器冷却水流量",
    "x52": "冷凝器冷却水流量",
}


def node_records(graph: KnowledgeGraph) -> list[dict[str, str | int]]:
    records: list[dict[str, str | int]] = []
    for name, node in sorted(graph.nodes.items(), key=lambda item: _node_sort_key(item[0])):
        style = KIND_STYLE.get(node.kind, KIND_STYLE["physical"])
        records.append(
            {
                "id": name,
                "label": name,
                "name_zh": node_label_zh(name, node.kind),
                "kind": node.kind,
                "kind_zh": KIND_LABELS_ZH.get(node.kind, node.kind),
                "color": style["color"],
                "size": style["size"],
            }
        )
    return records


def edge_records(graph: KnowledgeGraph) -> list[dict[str, str]]:
    return [
        {
            "source": triple.head,
            "target": triple.tail,
            "relation": triple.relation,
            "relation_zh": RELATION_LABELS_ZH.get(triple.relation, triple.relation),
            "color": RELATION_COLORS.get(triple.relation, "#64748b"),
        }
        for triple in graph.triples
    ]


def export_tep_pikg(output_dir: str | Path) -> dict[str, Path]:
    graph = build_tep_graph()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    files = {
        "nodes_csv": output / "tep_pikg_nodes.csv",
        "edges_csv": output / "tep_pikg_edges.csv",
        "neo4j_cypher": output / "neo4j_import.cypher",
        "graphml": output / "tep_pikg.graphml",
        "dot": output / "tep_pikg.dot",
        "html": output / "tep_pikg_viewer.html",
        "json": output / "tep_pikg.json",
    }
    write_csv(
        files["nodes_csv"],
        node_records(graph),
        ["id", "label", "name_zh", "kind", "kind_zh", "color", "size"],
    )
    write_csv(
        files["edges_csv"],
        edge_records(graph),
        ["source", "target", "relation", "relation_zh", "color"],
    )
    files["neo4j_cypher"].write_text(export_neo4j_import_cypher_text(), encoding="utf-8")
    files["graphml"].write_text(export_graphml_text(graph), encoding="utf-8")
    files["dot"].write_text(export_dot_text(graph), encoding="utf-8")
    files["json"].write_text(export_json_text(graph), encoding="utf-8")
    files["html"].write_text(export_html_text(graph), encoding="utf-8")
    return files


def write_csv(path: Path, rows: list[dict[str, str | int]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_graphml_text(graph: KnowledgeGraph) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="kind" for="node" attr.name="kind" attr.type="string"/>',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="name_zh" for="node" attr.name="name_zh" attr.type="string"/>',
        '  <key id="kind_zh" for="node" attr.name="kind_zh" attr.type="string"/>',
        '  <key id="color" for="node" attr.name="color" attr.type="string"/>',
        '  <key id="relation" for="edge" attr.name="relation" attr.type="string"/>',
        '  <key id="relation_zh" for="edge" attr.name="relation_zh" attr.type="string"/>',
        '  <graph id="TEP_PIKG" edgedefault="directed">',
    ]
    for record in node_records(graph):
        node_id = escape(str(record["id"]))
        lines.extend(
            [
                f'    <node id="{node_id}">',
                f'      <data key="label">{escape(str(record["label"]))}</data>',
                f'      <data key="name_zh">{escape(str(record["name_zh"]))}</data>',
                f'      <data key="kind">{escape(str(record["kind"]))}</data>',
                f'      <data key="kind_zh">{escape(str(record["kind_zh"]))}</data>',
                f'      <data key="color">{escape(str(record["color"]))}</data>',
                "    </node>",
            ]
        )
    for index, record in enumerate(edge_records(graph), start=1):
        source = escape(record["source"])
        target = escape(record["target"])
        relation = escape(record["relation"])
        relation_zh = escape(record["relation_zh"])
        lines.extend(
            [
                f'    <edge id="e{index}" source="{source}" target="{target}">',
                f'      <data key="relation">{relation}</data>',
                f'      <data key="relation_zh">{relation_zh}</data>',
                "    </edge>",
            ]
        )
    lines.extend(["  </graph>", "</graphml>", ""])
    return "\n".join(lines)


def export_dot_text(graph: KnowledgeGraph) -> str:
    lines = [
        "digraph TEP_PIKG {",
        '  graph [rankdir=LR, overlap=false, splines=true];',
        '  node [shape=ellipse, style=filled, fontname="Arial"];',
        '  edge [fontname="Arial", fontsize=9, arrowsize=0.7];',
    ]
    for record in node_records(graph):
        node_id = _dot_id(str(record["id"]))
        label = _dot_label(str(record["name_zh"]))
        color = str(record["color"])
        shape = "box" if record["kind"] == "device" else "ellipse"
        if record["kind"] == "variable":
            shape = "circle"
        lines.append(f'  {node_id} [label="{label}", fillcolor="{color}", shape={shape}];')
    for record in edge_records(graph):
        source = _dot_id(record["source"])
        target = _dot_id(record["target"])
        label = _dot_label(record["relation_zh"])
        color = record["color"]
        lines.append(f'  {source} -> {target} [label="{label}", color="{color}"];')
    lines.extend(["}", ""])
    return "\n".join(lines)


def export_json_text(graph: KnowledgeGraph) -> str:
    payload = {"nodes": node_records(graph), "edges": edge_records(graph)}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_neo4j_import_cypher_text() -> str:
    return """// Import TEP PIKG from tep_pikg_nodes.csv and tep_pikg_edges.csv.
// Put both CSV files in Neo4j's import directory before running this script.

CREATE CONSTRAINT tep_pikg_entity_id IF NOT EXISTS
FOR (n:TEP_PIKG) REQUIRE n.id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///tep_pikg_nodes.csv' AS row
MERGE (n:TEP_PIKG {id: row.id})
SET n.name = row.name_zh,
    n.name_en = row.label,
    n.name_zh = row.name_zh,
    n.kind = row.kind,
    n.kind_zh = row.kind_zh,
    n.color = row.color,
    n.size = toInteger(row.size)
FOREACH (_ IN CASE WHEN row.kind = 'variable' THEN [1] ELSE [] END | SET n:Variable)
FOREACH (_ IN CASE WHEN row.kind = 'stream' THEN [1] ELSE [] END | SET n:Stream)
FOREACH (_ IN CASE WHEN row.kind = 'device' THEN [1] ELSE [] END | SET n:Device)
FOREACH (_ IN CASE WHEN row.kind = 'substance' THEN [1] ELSE [] END | SET n:Substance);

LOAD CSV WITH HEADERS FROM 'file:///tep_pikg_edges.csv' AS row
MATCH (source:TEP_PIKG {id: row.source})
MATCH (target:TEP_PIKG {id: row.target})
FOREACH (_ IN CASE WHEN row.relation = 'State' THEN [1] ELSE [] END |
  MERGE (source)-[r:STATE]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
)
FOREACH (_ IN CASE WHEN row.relation = 'State of' THEN [1] ELSE [] END |
  MERGE (source)-[r:STATE_OF]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
)
FOREACH (_ IN CASE WHEN row.relation = 'Output' THEN [1] ELSE [] END |
  MERGE (source)-[r:OUTPUT]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
)
FOREACH (_ IN CASE WHEN row.relation = 'Contain' THEN [1] ELSE [] END |
  MERGE (source)-[r:CONTAIN]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
)
FOREACH (_ IN CASE WHEN row.relation = 'Contained by' THEN [1] ELSE [] END |
  MERGE (source)-[r:CONTAINED_BY]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
)
FOREACH (_ IN CASE WHEN row.relation = 'Generate' THEN [1] ELSE [] END |
  MERGE (source)-[r:GENERATE]->(target)
  SET r.relation = row.relation, r.name = row.relation_zh, r.color = row.color
);
"""


def export_html_text(graph: KnowledgeGraph) -> str:
    payload = {"nodes": node_records(graph), "edges": edge_records(graph)}
    data = json.dumps(payload, ensure_ascii=False)
    kind_labels = json.dumps(KIND_LABELS_ZH, ensure_ascii=False)
    relation_labels = json.dumps(RELATION_LABELS_ZH, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TEP PIKG 可视化</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #111827; background: #f8fafc; }}
    header {{ display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: #ffffff; }}
    h1 {{ margin: 0; font-size: 18px; }}
    .meta {{ display: flex; gap: 12px; font-size: 13px; color: #475569; }}
    #wrap {{ height: calc(100vh - 54px); display: grid; grid-template-columns: 1fr 260px; }}
    #canvas {{ width: 100%; height: 100%; background: #ffffff; }}
    aside {{ border-left: 1px solid #e5e7eb; background: #f8fafc; padding: 12px; overflow: auto; }}
    .legend {{ display: grid; gap: 8px; font-size: 13px; }}
    .item {{ display: flex; gap: 8px; align-items: center; }}
    .swatch {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
    .hint {{ margin-top: 16px; color: #64748b; font-size: 12px; line-height: 1.45; }}
    svg text {{ paint-order: stroke; stroke: #ffffff; stroke-width: 4px; stroke-linejoin: round; font-size: 10px; }}
    @media (max-width: 800px) {{ #wrap {{ grid-template-columns: 1fr; }} aside {{ display: none; }} }}
  </style>
</head>
<body>
  <header>
    <h1>TEP PIKG 可视化</h1>
    <div class="meta"><span id="nodeCount"></span><span id="edgeCount"></span></div>
  </header>
  <div id="wrap">
    <svg id="canvas" role="img" aria-label="TEP PIKG 网络可视化"></svg>
    <aside>
      <div class="legend" id="legend"></div>
      <div class="hint">拖拽节点可调整位置。滚动鼠标滚轮可缩放图谱。边标签显示关系类型。</div>
    </aside>
  </div>
  <script>
    const graph = {data};
    const kindLabels = {kind_labels};
    const relationLabels = {relation_labels};
    const svg = document.getElementById("canvas");
    const legend = document.getElementById("legend");
    document.getElementById("nodeCount").textContent = `${{graph.nodes.length}} 个节点`;
    document.getElementById("edgeCount").textContent = `${{graph.edges.length}} 条关系`;
    const kinds = [...new Map(graph.nodes.map(n => [n.kind, n.color])).entries()];
    legend.innerHTML = kinds.map(([kind, color]) => `<div class="item"><span class="swatch" style="background:${{color}}"></span>${{kindLabels[kind] || kind}}</div>`).join("");

    const width = () => svg.clientWidth || 900;
    const height = () => svg.clientHeight || 700;
    const ns = "http://www.w3.org/2000/svg";
    const root = document.createElementNS(ns, "g");
    svg.appendChild(root);
    const edges = document.createElementNS(ns, "g");
    const labels = document.createElementNS(ns, "g");
    const nodes = document.createElementNS(ns, "g");
    root.append(edges, labels, nodes);

    const nodeMap = new Map(graph.nodes.map((node, index) => {{
      const angle = (index / graph.nodes.length) * Math.PI * 2;
      return [node.id, {{...node, x: width()/2 + Math.cos(angle)*260, y: height()/2 + Math.sin(angle)*220, vx: 0, vy: 0}}];
    }}));
    const links = graph.edges.map(edge => ({{...edge, sourceNode: nodeMap.get(edge.source), targetNode: nodeMap.get(edge.target)}}));

    function makeLine(edge) {{
      const line = document.createElementNS(ns, "line");
      line.setAttribute("stroke", edge.color);
      line.setAttribute("stroke-opacity", "0.42");
      line.setAttribute("stroke-width", "1.1");
      return line;
    }}
    function makeEdgeLabel(edge) {{
      const text = document.createElementNS(ns, "text");
      text.textContent = relationLabels[edge.relation] || edge.relation;
      text.setAttribute("fill", edge.color);
      text.setAttribute("text-anchor", "middle");
      return text;
    }}
    function makeNode(node) {{
      const group = document.createElementNS(ns, "g");
      group.style.cursor = "grab";
      const circle = document.createElementNS(ns, "circle");
      circle.setAttribute("r", node.size);
      circle.setAttribute("fill", node.color);
      circle.setAttribute("stroke", "#ffffff");
      circle.setAttribute("stroke-width", "1.5");
      const text = document.createElementNS(ns, "text");
      text.textContent = node.name_zh || node.label;
      text.setAttribute("x", node.size + 3);
      text.setAttribute("y", "3");
      text.setAttribute("fill", "#111827");
      const title = document.createElementNS(ns, "title");
      title.textContent = `${{node.name_zh || node.label}}（${{kindLabels[node.kind] || node.kind}}）`;
      group.append(title, circle, text);
      group.addEventListener("pointerdown", event => {{
        event.preventDefault();
        group.setPointerCapture(event.pointerId);
        group.style.cursor = "grabbing";
        node.fx = node.x;
        node.fy = node.y;
      }});
      group.addEventListener("pointermove", event => {{
        if (node.fx === undefined) return;
        const point = clientToSvg(event.clientX, event.clientY);
        node.x = node.fx = point.x;
        node.y = node.fy = point.y;
        render();
      }});
      group.addEventListener("pointerup", event => {{
        group.releasePointerCapture(event.pointerId);
        group.style.cursor = "grab";
        node.fx = undefined;
        node.fy = undefined;
      }});
      return group;
    }}

    const edgeEls = links.map(edge => {{ const line = makeLine(edge); edges.appendChild(line); return line; }});
    const edgeLabelEls = links.map(edge => {{ const text = makeEdgeLabel(edge); labels.appendChild(text); return text; }});
    const nodeList = [...nodeMap.values()];
    const nodeEls = nodeList.map(node => {{ const el = makeNode(node); nodes.appendChild(el); return el; }});

    let zoom = 1, panX = 0, panY = 0;
    svg.addEventListener("wheel", event => {{
      event.preventDefault();
      zoom = Math.max(0.2, Math.min(3, zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
      root.setAttribute("transform", `translate(${{panX}},${{panY}}) scale(${{zoom}})`);
    }});

    function clientToSvg(clientX, clientY) {{
      const rect = svg.getBoundingClientRect();
      return {{ x: (clientX - rect.left - panX) / zoom, y: (clientY - rect.top - panY) / zoom }};
    }}

    function tick() {{
      for (const link of links) {{
        const dx = link.targetNode.x - link.sourceNode.x;
        const dy = link.targetNode.y - link.sourceNode.y;
        const dist = Math.max(20, Math.hypot(dx, dy));
        const force = (dist - 120) * 0.0012;
        const fx = dx * force;
        const fy = dy * force;
        link.sourceNode.vx += fx; link.sourceNode.vy += fy;
        link.targetNode.vx -= fx; link.targetNode.vy -= fy;
      }}
      for (let i = 0; i < nodeList.length; i++) {{
        for (let j = i + 1; j < nodeList.length; j++) {{
          const a = nodeList[i], b = nodeList[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist2 = Math.max(25, dx*dx + dy*dy);
          const force = 80 / dist2;
          a.vx -= dx * force; a.vy -= dy * force;
          b.vx += dx * force; b.vy += dy * force;
        }}
      }}
      for (const node of nodeList) {{
        node.vx += (width()/2 - node.x) * 0.0008;
        node.vy += (height()/2 - node.y) * 0.0008;
        if (node.fx === undefined) {{
          node.x += node.vx;
          node.y += node.vy;
        }}
        node.vx *= 0.86;
        node.vy *= 0.86;
      }}
      render();
      requestAnimationFrame(tick);
    }}

    function render() {{
      links.forEach((link, index) => {{
        edgeEls[index].setAttribute("x1", link.sourceNode.x);
        edgeEls[index].setAttribute("y1", link.sourceNode.y);
        edgeEls[index].setAttribute("x2", link.targetNode.x);
        edgeEls[index].setAttribute("y2", link.targetNode.y);
        edgeLabelEls[index].setAttribute("x", (link.sourceNode.x + link.targetNode.x) / 2);
        edgeLabelEls[index].setAttribute("y", (link.sourceNode.y + link.targetNode.y) / 2);
      }});
      nodeList.forEach((node, index) => nodeEls[index].setAttribute("transform", `translate(${{node.x}},${{node.y}})`));
    }}
    tick();
  </script>
</body>
</html>
"""


def _node_sort_key(name: str) -> tuple[int, str]:
    if name.startswith("x") and name[1:].isdigit():
        return (0, f"{int(name[1:]):03d}")
    if name.startswith("Stream "):
        return (1, f"{int(name.split()[1]):03d}")
    return (2, name)


def node_label_zh(name: str, kind: str) -> str:
    if kind == "variable":
        return f"{name} {VARIABLE_LABELS_ZH.get(name, '变量')}"
    if kind == "stream":
        if name.startswith("Stream "):
            return name.replace("Stream", "流股")
        return STREAM_LABELS_ZH.get(name, name)
    if kind == "device":
        return DEVICE_LABELS_ZH.get(name, name)
    if kind == "substance":
        return SUBSTANCE_LABELS_ZH.get(name, f"物质{name}")
    return name


def _dot_id(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dot_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
