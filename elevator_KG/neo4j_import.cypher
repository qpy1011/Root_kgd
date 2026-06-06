// Elevator KG Neo4j import script. Put elevator_kg_nodes.csv and elevator_kg_edges.csv in Neo4j's import directory.
CREATE CONSTRAINT elevator_kg_node_id IF NOT EXISTS FOR (n:ElevatorKG) REQUIRE n.id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_nodes.csv' AS row
MERGE (n:ElevatorKG {id: row.id})
SET n.label = row.label,
    n.name = row.name,
    n.name_en = row.name_en,
    n.kind = row.kind,
    n.kind_zh = row.kind_zh,
    n.description = row.description,
    n.source = row.source,
    n.source_url = row.source_url,
    n.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    n.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    n.trapped_people = row.trapped_people,
    n.rescue_minutes = row.rescue_minutes,
    n.color = row.color,
    n.size = CASE row.size WHEN '' THEN null ELSE toInteger(row.size) END;

// BELONGS_TO_SYSTEM
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'BELONGS_TO_SYSTEM'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:BELONGS_TO_SYSTEM]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// CATEGORIZED_AS
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'CATEGORIZED_AS'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:CATEGORIZED_AS]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// CAUSES_PHENOMENON
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'CAUSES_PHENOMENON'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:CAUSES_PHENOMENON]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// CHECKS_COMPONENT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'CHECKS_COMPONENT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:CHECKS_COMPONENT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// COVERS_SAFETY_TOPIC
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'COVERS_SAFETY_TOPIC'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:COVERS_SAFETY_TOPIC]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// DEFINES_MAINTENANCE_SCOPE
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'DEFINES_MAINTENANCE_SCOPE'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:DEFINES_MAINTENANCE_SCOPE]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// DERIVED_FROM
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'DERIVED_FROM'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:DERIVED_FROM]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HANDLED_BY
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HANDLED_BY'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HANDLED_BY]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_AGGREGATE_CAUSE
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_AGGREGATE_CAUSE'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_AGGREGATE_CAUSE]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_COMPONENT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_COMPONENT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_COMPONENT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_FAULT_CATEGORY
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_FAULT_CATEGORY'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_FAULT_CATEGORY]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_FAULT_LOCATION
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_FAULT_LOCATION'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_FAULT_LOCATION]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_FAULT_PHENOMENON
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_FAULT_PHENOMENON'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_FAULT_PHENOMENON]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_RAW_FAULT_TEXT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_RAW_FAULT_TEXT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_RAW_FAULT_TEXT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_REPLACED_PART_TYPE
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_REPLACED_PART_TYPE'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_REPLACED_PART_TYPE]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_ROOT_COMPONENT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_ROOT_COMPONENT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_ROOT_COMPONENT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_SITE_TYPE
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_SITE_TYPE'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_SITE_TYPE]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// HAS_SYSTEM
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'HAS_SYSTEM'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:HAS_SYSTEM]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// LIKELY_AFFECTS
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'LIKELY_AFFECTS'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:LIKELY_AFFECTS]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// LOCATED_AT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'LOCATED_AT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:LOCATED_AT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// MAINTAINED_BY
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'MAINTAINED_BY'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:MAINTAINED_BY]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// MANUFACTURED_BY
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'MANUFACTURED_BY'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:MANUFACTURED_BY]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// MAPS_TO_COMPONENT
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'MAPS_TO_COMPONENT'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:MAPS_TO_COMPONENT]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// MAPS_TO_SYSTEM
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'MAPS_TO_SYSTEM'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:MAPS_TO_SYSTEM]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// MITIGATES
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'MITIGATES'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:MITIGATES]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// OBSERVED_PHENOMENON
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'OBSERVED_PHENOMENON'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:OBSERVED_PHENOMENON]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// PART_OF_SAFETY_CHAIN
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'PART_OF_SAFETY_CHAIN'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:PART_OF_SAFETY_CHAIN]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// RECOMMENDS_ACTION
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'RECOMMENDS_ACTION'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:RECOMMENDS_ACTION]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// REPORTED_ON
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'REPORTED_ON'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:REPORTED_ON]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// SUPPORTS_CATEGORY
LOAD CSV WITH HEADERS FROM 'file:///elevator_kg_edges.csv' AS row
WITH row WHERE row.relation = 'SUPPORTS_CATEGORY'
MATCH (s:ElevatorKG {id: row.source})
MATCH (t:ElevatorKG {id: row.target})
MERGE (s)-[r:SUPPORTS_CATEGORY]->(t)
SET r.name = row.relation_zh,
    r.relation = row.relation,
    r.evidence = row.evidence,
    r.source_doc = row.source_doc,
    r.source_url = row.source_url,
    r.count = CASE row.count WHEN '' THEN null ELSE toInteger(row.count) END,
    r.weight = CASE row.weight WHEN '' THEN null ELSE toFloat(row.weight) END,
    r.color = row.color;

// Example queries:
// MATCH p=(:ElevatorKG {name:'困人'})<-[:CAUSES_PHENOMENON]-(:ElevatorKG)-[:LIKELY_AFFECTS|HAS_ROOT_COMPONENT]->() RETURN p LIMIT 50;
// MATCH p=(:ElevatorKG {name:'门系统'})--() RETURN p LIMIT 100;
// MATCH (c:ElevatorKG {kind:'fault_category'})<-[r:HAS_FAULT_CATEGORY]-(:ElevatorKG {kind:'work_order'}) RETURN c.name, count(r) AS n ORDER BY n DESC;