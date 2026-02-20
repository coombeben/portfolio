---
applyTo: "**/*.yaml,**/*.yml"
---
# Instructions

You are helping to build a knowledge graph of my work.

## Context

I am building a knowledge graph of my work to power a graph RAG system. 
This system will form an "interactive portfolio".
It is **not** designed to say everything about me, rather:
1. How I think
2. What I've built
3. Why I made the choices I did
4. My taste

That is, the knowledge base should be opinionated, structured, written for engineers, and explicit about tradeoffs.
Some good example questions to keep in mind:
- "Tell me about a project where you owned the system end-to-end."
- "Why did you choose X instead of Y?"
- "How did you chunk and embed the data?"
- "What's something you got wrong in a past project?"

## Task

Your task is to build the graph, step-by-step.
I will start by providing you with some basic information about a project.
Across multiple conversation turns, you will:
1. Add new nodes and relationships to the graph.
2. Update existing nodes and relationships (if something has changed).
3. Ask me follow-up questions to gather more information.

### Rules

- **Important**: Nodes must ALWAYS be meaningful. NEVER create generic, "fluffy" nodes which don't add value.
- `Person`, `Philosophy`, `Technology` and `Skill` nodes belong in `global.yaml`. All other nodes belong in `{project-name}.yaml`
- At the start, you probably won't have enough information to create a full graph – that's OK! Just create what you can, and ask me for more details.
- Try and make sure that each `Constraint` is addressed by at least one `Decision`.
- The following relationships will be created automatically. You do not need to create them:
  - `(Person)-[:BUILT]->(Project)`
  - `(Project)-[:ENCOUNTERED]->(Constraint)`
  - `(Project)-[:LEAD_TO]->(Outcome)`
  - `(Project)-[:COMPOSED_OF]->(ArchitectureComponent)`
- If an `ArchitectureComponent` is implemented with parent/child technologies (e.g. "Python" and "PyTorch"), only create the relationship for the child node (e.g. "PyTorch").

# Schema

## Nodes

- `Person` (`name`, `bio`): **Root Node.** Me
- `Project` (`name`, `summary`): A high-level container for a specific work item
- `Outcome` (`type`, `description`): A tangiable result of a project. Type is one of `result | learning | reflection`.
- `Philosophy` (`statement`): My core beliefs and approaches towards my tasks.
- `Decision` (`description`, `reasoning`, `tradeoff`): A specific choice made during development.
- `ArchitectureComponent` (`name`, `detail`): Specific sub-systems (e.g., "Ingestion Pipeline"). Allows for technical deep dives
- `Constraint` (`name`, `description`): External pressures (e.g., "Low Budget," "Latency").
- `Technology` (`name`, `specificity`, `role`, `thoughts`): Languages, frameworks, or tools used.
- `Skill` (`name`): A specific, high-level skill.

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
