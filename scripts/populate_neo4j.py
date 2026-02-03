import os

import yaml
from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm

load_dotenv()

# Define the graph schema
NODE_TYPES = {
    'Person': {'name', 'bio'},
    'Project': {'name', 'summary'},
    'Outcome': {'description'},
    'Philosophy': {'statement'},
    'Decision': {'description', 'reasoning', 'tradeoff'},
    'ArchitectureComponent': {'name', 'detail'},
    'Constraint': {'name', 'description'},
    'Technology': {'name', 'thoughts'},
    'Skill': {'name'},
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
    ('ArchitectureComponent', 'DEMONSTRATES', 'Skill')
]
RELATIONSHIP_TYPES = {relation[1] for relation in RELATIONS}

# Sanity checks
assert all(relation[0] in NODE_TYPES for relation in RELATIONS)
assert len(RELATIONSHIP_TYPES) == len(RELATIONS)
assert all(relation[2] in NODE_TYPES for relation in RELATIONS)


URI = "neo4j://localhost"
AUTH = tuple(os.environ.get("NEO4J_AUTH").split('/'))
PROJECTS = ['global.yaml', 'trade-agent.yaml', 'funding-finder.yaml', 'virtual-analyst.yaml']


def load_data(filename: str) -> dict:
    """Loads data from a YAML file into a dictionary.
    Validates the data against the defined schema."""
    with open(filename, 'r') as f:
        projects = yaml.safe_load(f)

    # Validate
    node_ids = set()
    for node in projects['nodes']:
        # Check node type is valid
        if node['type'] not in NODE_TYPES:
            raise ValueError(f"Invalid node type for \"{node['id']}\": {node['type']}")

        # Check node id is unique
        if node['id'] in node_ids:
            raise ValueError(f"Duplicate node id: {node['id']}")

        node_ids.add(node['id'])

    for relationship in projects['relationships']:
        # Check relationship type is valid
        if relationship['type'] not in RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type for: \"{relationship}\"")

    return projects


def populate_neo4j(session, data: dict) -> tuple[int, int]:
    # Create nodes
    print("Creating nodes...")
    for node in data['nodes']:
        node_id = node['id']
        node_type = node['type']
        properties = {k: v for k, v in node.items() if v not in {'id', 'type'}}

        # Build the Cypher query
        props_string = ", ".join([f"{key}: ${key}" for key in properties.keys()])
        query = f"CREATE (n:{node_type} {{id: $id, {props_string}}})"

        # Execute with parameters
        params = {'id': node_id, **properties}
        session.run(query, params)

    # Create relationships
    print("Creating relationships...")
    for relationship in data['relationships']:
        from_id = relationship['from']
        to_id = relationship['to']
        rel_type = relationship['type']

        query = f"""
        MATCH (from {{id: $from_id}})
        MATCH (to {{id: $to_id}})
        CREATE (from)-[:{rel_type}]->(to)
        """

        session.run(query, {'from_id': from_id, 'to_id': to_id})

    return len(data['nodes']), len(data['relationships'])


inserted_nodes, inserted_relationships = 0, 0
with GraphDatabase.driver(URI, auth=AUTH) as driver:

    driver.verify_connectivity()
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")

        for file in tqdm(PROJECTS):
            data = load_data(f'../data/{file}')
            delta_nodes, delta_relationships = populate_neo4j(session, data)
            inserted_nodes += delta_nodes
            inserted_relationships += delta_relationships

print(f"Inserted {inserted_nodes} nodes and {inserted_relationships} relationships.")
