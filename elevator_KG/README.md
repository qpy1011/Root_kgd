# 电梯故障知识图谱

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
