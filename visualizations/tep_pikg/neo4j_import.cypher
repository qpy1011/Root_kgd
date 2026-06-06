// Import TEP PIKG from tep_pikg_nodes.csv and tep_pikg_edges.csv.
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
