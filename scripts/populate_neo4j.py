import os

import yaml
from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

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
AUTH = ('neo4j', os.getenv('NEO4J_PASSWORD'))
GLOBALS = 'global.yaml'
PROJECTS = ['trade-agent.yaml', 'funding-finder.yaml', 'virtual-analyst.yaml', 'this-project.yaml']
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
EMBEDDING_BATCH_SIZE = 32


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
            raise ValueError(f"Invalid node type for \"{node['uid']}\": {node['type']}")

        # Check node uid is unique
        if node['uid'] in node_ids:
            raise ValueError(f"Duplicate node ID: {node['uid']}")

        node_ids.add(node['uid'])

    for relationship in projects['relationships']:
        # Check relationship type is valid
        if relationship['type'] not in RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type for: \"{relationship}\"")

    return projects


def clear_neo4j(session):
    session.run("MATCH (n) DETACH DELETE n")
    session.run("DROP INDEX contentIndex IF EXISTS")
    session.run("DROP INDEX embeddingIndex IF EXISTS")


def populate_neo4j(session, data: dict) -> tuple[int, int]:
    # Create nodes
    for node in data['nodes']:
        node_id = node['uid']
        node_type = node['type']
        properties = {k: v for k, v in node.items() if k not in {'uid', 'type'}}

        # Create a content property for full-text search
        str_properties = "\n".join(f"{k}: {v}" for k, v in properties.items())
        content = f"{node_type}\n{str_properties}"
        properties['content'] = content

        # Build the Cypher query with both semantic label and Searchable label
        props_string = ", ".join([f"{key}: ${key}" for key in properties.keys()])
        query = f"CREATE (n:{node_type}:Searchable {{uid: $uid, {props_string}}})"

        # Execute with parameters
        params = {'uid': node_id, **properties}
        session.run(query, params)

    # Create relationships
    for relationship in data['relationships']:
        from_id = relationship['from']
        to_id = relationship['to']
        rel_type = relationship['type']

        query = f"""
        MATCH (from {{uid: $from_id}})
        MATCH (to {{uid: $to_id}})
        CREATE (from)-[:{rel_type}]->(to)
        """

        session.run(query, {'from_id': from_id, 'to_id': to_id})

    return len(data['nodes']), len(data['relationships'])


def create_embeddings(session, model: SentenceTransformer, batch_size: int = EMBEDDING_BATCH_SIZE):
    """Create embeddings for all Searchable nodes in batches without loading all into memory."""
    # Get total count
    result = session.run("MATCH (n:Searchable) RETURN count(n) as total")
    total_nodes = result.single()['total']

    print(f"Creating embeddings for {total_nodes} nodes in batches of {batch_size}...")

    # Process in chunks
    offset = 0
    with tqdm(total=total_nodes) as pbar:
        while offset < total_nodes:
            # Fetch a batch of nodes
            result = session.run(
                "MATCH (n:Searchable) RETURN n.uid as uid, n.content as content SKIP $offset LIMIT $limit",
                {'offset': offset, 'limit': batch_size}
            )
            batch = [(record['uid'], record['content']) for record in result]

            if not batch:
                break

            uids = [uid for uid, _ in batch]
            contents = [content for _, content in batch]

            # Generate embeddings for the batch
            embeddings = model.encode(contents, show_progress_bar=False)

            # Update nodes with embeddings
            for uid, embedding in zip(uids, embeddings):
                session.run(
                    "MATCH (n:Searchable {uid: $uid}) SET n.embedding = $embedding",
                    {'uid': uid, 'embedding': embedding.tolist()}
                )

            offset += len(batch)
            pbar.update(len(batch))


def create_indexes(session, embedding_dim: int):
    session.run("""
        CREATE FULLTEXT INDEX contentIndex
        FOR (n:Searchable)
        ON EACH [n.content]
        OPTIONS {
            indexConfig: {
                `fulltext.analyzer`: 'english'
            }
        }
        """)
    session.run(f"""
        CREATE VECTOR INDEX embeddingIndex
        FOR (n:Searchable)
        ON n.embedding
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {embedding_dim},
                `vector.similarity_function`: 'cosine'
            }}
        }}
    """)


def main():
    print("Intialising SentenceTransformer model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embedding_dim = model.get_sentence_embedding_dimension()

    print("Populating Neo4j database...")
    inserted_nodes, inserted_relationships = 0, 0
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()

        with driver.session() as session:
            # Clear existing data
            clear_neo4j(session)

            for file in tqdm([GLOBALS] + PROJECTS):
                data = load_data(f'../data/{file}')
                delta_nodes, delta_relationships = populate_neo4j(session, data)
                inserted_nodes += delta_nodes
                inserted_relationships += delta_relationships

            print(f"Inserted {inserted_nodes} nodes and {inserted_relationships} relationships.")

            # Create embeddings in batches
            print("Creating embeddings...")
            create_embeddings(session, model)
            # Create full-text index on Searchable nodes
            create_indexes(session, embedding_dim)


if __name__ == "__main__":
    main()
