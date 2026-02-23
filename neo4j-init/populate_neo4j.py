# /// script
# dependencies = [
#   "pyyaml",
#   "neo4j",
# ]
# [tool.uv]
# exclude-newer = "2026-02-20T00:00:00Z"
# ///
"""
Script to populate a Neo4j database with data from the project files.

This script has two main purposes:
1. Populate the database with the initial data from the project files. This includes creating
 implied relationships between nodes based on their types, as well as creating embeddings for
 Searchable nodes.
2. Sanity check the data against the defined schema. As the YAML files are created using an LLM,
 there is a risk of hallucinated or malformed data. This script will raise errors if the data
 doesn't conform to the expected structure, ensuring that only valid data is inserted into the
 database.

Steps:
1. Prepare the database by clearing existing data and creating necessary constraints and indexes.
2. Load the global data from the GLOBALS file.
3. Load the project data from the PROJECTS files.
4. Create implicit relationships between nodes based on their types.
5. Create BELONGS_TO_PROJECT relationships for all nodes in the project files.
6. Create embeddings for all Searchable nodes.
"""
import os
from pathlib import Path

import yaml
from neo4j import GraphDatabase, Session


# Define the graph schema
NODE_TYPES = {
    'Person': {'name', 'bio'},
    'Project': {'name', 'summary'},
    'Outcome': {'type', 'description'},
    'Philosophy': {'statement'},
    'Decision': {'description', 'reasoning', 'tradeoff'},
    'ArchitectureComponent': {'name', 'detail'},
    'Constraint': {'name', 'description'},
    'Technology': {'name', 'specificity', 'role', 'thoughts'},
    'Skill': {'name'},
    'Searchable': {'content', 'embedding'}  # Meta-label. Used for hybrid search.
}
RELATIONS = [
    ('Person', 'BUILT', 'Project'),
    ('Person', 'BELIEVES', 'Philosophy'),
    ('Philosophy', 'GUIDED', 'Decision'),
    ('Project', 'ENCOUNTERED', 'Constraint'),
    ('Project', 'COMPOSED_OF', 'ArchitectureComponent'),
    ('Project', 'LEAD_TO', 'Outcome'),
    ('Decision', 'ADDRESSED', 'Constraint'),
    ('Decision', 'SHAPED', 'ArchitectureComponent'),
    ('ArchitectureComponent', 'IMPLEMENTED_WITH', 'Technology'),
    ('ArchitectureComponent', 'DEMONSTRATES', 'Skill'),
    ('Technology', 'CHILD_OF', 'Technology'),
    ('*', 'BELONGS_TO_PROJECT', 'Project')  # Special case - can be from any node to a Project
]
RELATIONSHIP_TYPES = {relation[1] for relation in RELATIONS}

# Sanity checks
assert all(relation[0] in NODE_TYPES for relation in RELATIONS if relation[0] != '*')
assert len(RELATIONSHIP_TYPES) == len(RELATIONS)
assert all(relation[2] in NODE_TYPES for relation in RELATIONS)


GLOBALS = 'global.yaml'
PROJECTS = [
    'trade-agent.yaml', 'funding-finder.yaml', 'virtual-analyst.yaml', 'this-project.yaml',
    'form-autocomplete.yaml'
]
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_DIM = 384
DATA_DIR = Path('/data')
if not DATA_DIR.exists():
    raise ValueError(f"Data directory not found: {DATA_DIR}")


def load_data(path: Path) -> dict:
    """Loads data from a YAML file into a dictionary.
    Validates the data against the defined schema."""
    with path.open('r', encoding='utf-8') as f:
        projects = yaml.safe_load(f)

    # Validate
    node_ids = set()
    for node_type, node_list in projects['nodes'].items():
        # Check node type is valid
        if node_type not in NODE_TYPES:
            raise ValueError(f"Invalid node type: {node_type}")

        for node in node_list:
            # Check node uid is unique
            if node['uid'] in node_ids:
                raise ValueError(f"Duplicate node ID: {node['uid']}")
            node_ids.add(node['uid'])

    for rel_type, rel_list in projects['relationships'].items():
        # Check relationship type is valid
        if rel_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type: \"{rel_type}\"")

    return projects


def prepare_neo4j(session: Session, embedding_dim: int = EMBEDDING_DIM) -> None:
    """Prepares the Neo4j database by clearing existing data and creating necessary constraints and indexes."""
    # Clear existing data
    session.run("MATCH (n) DETACH DELETE n")

    # Ensure UID is unique across all nodes
    session.run("CREATE CONSTRAINT global_uid_uniqueness IF NOT EXISTS "
                "FOR (n:Base) REQUIRE n.uid IS UNIQUE")

    # Ideally, we'd create property existence constraints too, but that's an Enterprise feature -_-

    # Create indexes for fast lookup of nodes by UID
    session.run("CREATE INDEX base_uid_index IF NOT EXISTS FOR (n:Base) ON (n.uid)")

    # Create indexes for fast lookup of nodes by semantic label
    session.run("""
        CREATE FULLTEXT INDEX contentIndex IF NOT EXISTS
        FOR (n:Searchable)
        ON EACH [n.content]
        OPTIONS {
            indexConfig: {
                `fulltext.analyzer`: 'english'
            }
        }
        """)
    session.run(f"""
        CREATE VECTOR INDEX embeddingIndex IF NOT EXISTS
        FOR (n:Searchable)
        ON n.embedding
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
    """)


def populate_neo4j(session: Session, data: dict) -> tuple[int, int]:
    """Creates the nodes and relationships from the data files."""
    total_nodes, total_relationships = 0, 0

    # Create nodes
    for node_type, node_list in data['nodes'].items():
        for node in node_list:
            node_id = node['uid']
            properties = {k: v for k, v in node.items() if k != 'uid'}

            # Create a content property for full-text search
            str_properties = "\n".join(f"{k}: {v}" for k, v in properties.items())
            content = f"{node_type}\n{str_properties}"
            properties['content'] = content

            # Build the Cypher query with: semantic label, Base label, and Searchable label
            props_string = ", ".join([f"{key}: ${key}" for key in properties.keys()])
            # "Person" shouldn't appear in search results, so don't give it the Searchable label
            extra_labels = 'Base:Searchable' if node_type != 'Person' else 'Base'
            query = f"CREATE (n:{node_type}:{extra_labels} {{uid: $uid, {props_string}}})"

            params = {'uid': node_id, **properties}
            session.run(query, params)
            total_nodes += 1

    # Create relationships
    for rel_type, rel_list in data['relationships'].items():
        for relationship in rel_list:
            from_id = relationship['from']
            to_id = relationship['to']

            query = f"""
            MATCH (from {{uid: $from_id}})
            MATCH (to {{uid: $to_id}})
            CREATE (from)-[:{rel_type}]->(to)
            """

            session.run(query, {'from_id': from_id, 'to_id': to_id})
            total_relationships += 1

    return total_nodes, total_relationships


def create_project_relationships(session: Session, data: dict) -> int:
    """Create BELONGS_TO_PROJECT relationships for all nodes in a project file."""
    # Find the Project node in this file
    project_uid = None
    if 'Project' in data['nodes']:
        project_nodes = data['nodes']['Project']
        if project_nodes:
            project_uid = project_nodes[0]['uid']

    if not project_uid:
        raise ValueError("No Project node found in this file.")

    # Collect all unique UIDs referenced in this file (from nodes and relationships)
    referenced_uids = set()

    # Add UIDs from nodes
    for node_list in data['nodes'].values():
        for node in node_list:
            referenced_uids.add(node['uid'])

    # Add UIDs from relationships
    for rel_list in data['relationships'].values():
        for relationship in rel_list:
            referenced_uids.add(relationship['from'])
            referenced_uids.add(relationship['to'])

    # Remove the project UID itself
    referenced_uids.discard(project_uid)

    # Create BELONGS_TO_PROJECT relationships for all referenced UIDs
    for uid in referenced_uids:
        query = """
        MATCH (n {uid: $node_uid})
        MATCH (p:Project {uid: $project_uid})
        CREATE (n)-[:BELONGS_TO_PROJECT]->(p)
        """
        session.run(query, {'node_uid': uid, 'project_uid': project_uid})

    return len(referenced_uids)


def create_embeddings(
    session: Session,
    batch_size: int = EMBEDDING_BATCH_SIZE
) -> None:
    """Create embeddings for all Searchable nodes in batches."""
    query = f"""
    MATCH (s:Searchable WHERE s.content IS NOT NULL)
    WITH collect(s) AS searchableList, 
         count(*) AS total,
         $batch_size AS batchSize 
    UNWIND range(0, total-1, batchSize) AS batchStart 
    CALL (searchableList, batchStart, batchSize) {{
        WITH [searchable IN searchableList[batchStart .. batchStart + batchSize] | searchable.content] AS batch 
        CALL ai.text.embedBatch(batch, 'OpenAI', {{ token: '-', model: '{os.environ["HF_EMBEDDING_MODEL"]}' }}) YIELD index, vector
        CALL db.create.setNodeVectorProperty(searchableList[batchStart + index], 'embedding', toFloatList(vector)) 
    }} IN CONCURRENT TRANSACTIONS OF 1 ROW
    """
    session.run(query, {'batch_size': batch_size})
    return


def create_implicit_relationships(session: Session, data: dict) -> int:
    """Create relationships that are implied by node types within a project file,
    removing the need to manually specify them in the YAML:
      - Person (me) -> BUILT -> Project
      - Project -> ENCOUNTERED -> Constraint
      - Project -> COMPOSED_OF -> ArchitectureComponent
      - Project -> LEAD_TO -> Outcome
    """
    implicit_relations = [
        ('Person', 'BUILT', 'Project'),
        ('Project', 'ENCOUNTERED', 'Constraint'),
        ('Project', 'COMPOSED_OF', 'ArchitectureComponent'),
        ('Project', 'LEAD_TO', 'Outcome'),
    ]

    total = 0
    for from_type, rel_type, to_type in implicit_relations:
        from_nodes = data['nodes'].get(from_type, [])
        to_nodes = data['nodes'].get(to_type, [])

        if not from_nodes or not to_nodes:
            continue

        for from_node in from_nodes:
            for to_node in to_nodes:
                query = f"""
                MATCH (from:{from_type} {{uid: $from_uid}})
                MATCH (to:{to_type} {{uid: $to_uid}})
                MERGE (from)-[:{rel_type}]->(to)
                """
                session.run(query, {'from_uid': from_node['uid'], 'to_uid': to_node['uid']})
                total += 1

    return total


def create_implicit_implemented_with(session: Session) -> int:
    """For any ArchitectureComponent that IMPLEMENTED_WITH a child Technology,
    also create IMPLEMENTED_WITH relationships to all ancestor Technologies
    via CHILD_OF chains."""
    result = session.run("""
        MATCH (c:ArchitectureComponent)-[:IMPLEMENTED_WITH]->(child:Technology)-[:CHILD_OF*1..]->(ancestor:Technology)
        WHERE NOT (c)-[:IMPLEMENTED_WITH]->(ancestor)
        MERGE (c)-[:IMPLEMENTED_WITH]->(ancestor)
        RETURN count(*) as total
    """)
    return result.single()['total']


def main():
    print("Populating Neo4j database...")
    neo4j_uri = os.environ['NEO4J_URI']
    neo4j_auth = ('neo4j', os.getenv('NEO4J_PASSWORD'))

    inserted_nodes, inserted_relationships = 0, 0
    with GraphDatabase.driver(neo4j_uri, auth=neo4j_auth) as driver:
        driver.verify_connectivity()

        with driver.session() as session:
            # Clear existing data, create constraints and indexes
            prepare_neo4j(session)

            # Process global file
            data = load_data(DATA_DIR / GLOBALS)
            delta_nodes, delta_relationships = populate_neo4j(session, data)
            inserted_nodes += delta_nodes
            inserted_relationships += delta_relationships

            # Process project files
            for file in PROJECTS:
                data = load_data(DATA_DIR / file)
                delta_nodes, delta_relationships = populate_neo4j(session, data)
                inserted_nodes += delta_nodes
                inserted_relationships += delta_relationships

                # Create implicit relationships (derived from node types)
                implicit_rels = create_implicit_relationships(session, data)
                inserted_relationships += implicit_rels

                # Create BELONGS_TO_PROJECT relationships
                project_rels = create_project_relationships(session, data)
                inserted_relationships += project_rels

            # Create implicit IMPLEMENTED_WITH relationships to parent technologies
            implicit_tech_rels = create_implicit_implemented_with(session)
            inserted_relationships += implicit_tech_rels
            print(f"Inserted {inserted_nodes} nodes and {inserted_relationships} relationships.")

            # Create embeddings in batches
            print('Creating embeddings...')
            create_embeddings(session)

            print('Done!')


if __name__ == "__main__":
    main()
