# Schema

The `neo4j-init.py` script populates the database with the following schema

## Nodes

- `Person` (`name`, `bio`): **Root Node.** Me
- `Project` (`name`, `summary`): A high-level container for a specific work item
- `Outcome` (`type`, `description`): A tangiable result of a project. `type` is one of `result | learning | reflection`.
- `Philosophy` (`statement`): My core beliefs and approaches towards my tasks.
- `Decision` (`description`, `reasoning`, `tradeoff`): A specific choice made during development.
- `ArchitectureComponent` (`name`, `detail`): Specific sub-systems (e.g., "Ingestion Pipeline"). Allows for technical deep dives
- `Constraint` (`name`, `description`): External pressures (e.g., "Low Budget," "Latency").
- `Technology` (`name`, `specificity`, `role`, `thoughts`): Languages, frameworks, or tools used. `specificity` is one of `1 | 2 | 3`.
- `Skill` (`name`): A specific, high-level skill.
- `Searchable` (`content`, `embedding`): *Automatically generated*. Indicates a node that can be retrieved via vector search. `content` is the text used to generate the embedding.

## Relationships

- `(Person)-[:BUILT]->(Project)`: Connects me to my work.
- `(Person)-[:BELIEVES]->(Philosophy)`: Connects me to my guiding principles.
- `(Philosophy)-[:GUIDED]->(Decision)`: Shows how a belief influenced a specific choice.
- `(Project)-[:ENCOUNTERED]->(Constraint)`: Sets the context/difficulty for the project.
- `(Project)-[:COMPOSED_OF]->(ArchitectureComponent)`: Breaks a project down into technical modules.
- `(Project)-[:LEAD_TO]->(Outcome)`: Shows a result of a project.
- `(Decision)-[:ADDRESSED]->(Constraint)`: Proves problem-solving (Decision X solved Constraint Y).
- `(Decision)-[:SHAPED]->(ArchitectureComponent)`: Connects choice to physical implementation.
- `(ArchitectureComponent)-[:IMPLEMENTED_WITH]->(Technology)`: Final mapping of architecture to specific tools.
- `(ArchitectureComponent)-[:DEMONSTRATES]->(Skill)`: Evidences skills in projects.
- `(Technology)-[:CHILD_OF]->(Technology)`: Links a specific tool to its parent. Reduces the need for manual mapping on a per-project basis.
- `(*)-[:BELONGS_TO_PROJECT]->(Project)`:  *Automatically generated*. Connects a node to a project. Makes it easier to find relevant projects from nodes.
