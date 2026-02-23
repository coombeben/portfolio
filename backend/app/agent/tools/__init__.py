"""
Tools for the LangGraph agent.

Provides three tools:
- `search_knowledge_base`: Perform hybrid semantic and keyword search across the knowledge graph to
    identify projects relevant to a natural language query.
- `get_project_detail`: Retrieve detailed information about a specific project.
- `summarise_global_patterns`: Analyse and aggregate recurring technologies, skills, or philosophies
    across projects.
"""
from typing import Literal, Iterable

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from .types import ProjectMatch, Evidence, ProjectDetail, Pattern, GlobalPatternSummary
from app.agent.models import AgentContext

__all__ = ['search_knowledge_base', 'get_project_detail', 'summarise_global_patterns']

Focus = Literal['TECHNICAL', 'STRATEGIC', 'RESULTS']


def _labels_to_focus(labels: list[str]) -> Focus | None:
    """Convert a list of labels to a focus area."""
    for label in labels:
        # Ignore meta label
        if label == 'Searchable':
            continue

        if label in ('Technology', 'Skill', 'ArchitectureComponent'):
            return 'TECHNICAL'
        if label in ('Decision', 'Constraint', 'Philosophy'):
            return 'STRATEGIC'
        if label == 'Outcome':
            return 'RESULTS'

    return None


# noinspection PyIncorrectDocstring
@tool
async def search_knowledge_base(
    query: str,
    runtime: ToolRuntime[AgentContext],
) -> list[ProjectMatch]:
    """Perform hybrid semantic and keyword search across the knowledge graph to identify
    projects relevant to a natural language query.

    Returns projects ranked by relevance, along with supporting evidence nodes that
    explain why each project matched. Intended as an entry-point discovery tool that
    helps select project IDs and guide follow-up retrieval using `get_project_detail`.

    Args:
        query: The natural language query to search for against the hybrid index

    Returns:
        The top 5 most relevant projects with scores and supporting evidence.
    """
    MAX_NODES = 30
    CANDIDATE_POOL = 60
    MAX_PROJECTS = 5
    MAX_EVIDENCE = 3

    cypher = """
    // Generate the embedding
    WITH ai.text.embed($query_, "openai", { token: '-', model: 'text-embeddings-inference' }) AS vector
    WITH toFloatList(vector) AS queryVector, 
         $query_ as query
    
    // Execute searches within a unified subquery
    CALL (queryVector, query) {
        // Branch A: Vector Search
        WITH queryVector
        MATCH (n)
        SEARCH n IN (
            VECTOR INDEX embeddingIndex
            FOR queryVector
            LIMIT $max_nodes
        ) SCORE AS vectorScore
        ORDER BY vectorScore DESC
        
        // Create the rank index (1-based)
        WITH collect(n) AS vNodes
        UNWIND range(0, size(vNodes)-1) AS vIdx
        RETURN vNodes[vIdx] AS n, (vIdx + 1) AS vRank, 0 AS fRank
    
        UNION ALL
    
        // Branch B: Fulltext Search
        WITH query
        CALL db.index.fulltext.queryNodes("contentIndex", query)
        YIELD node AS n, score AS fulltextScore
        ORDER BY fulltextScore DESC
        LIMIT $max_nodes
        
        // Create the rank index (1-based)
        WITH collect(n) AS fNodes
        UNWIND range(0, size(fNodes)-1) AS fIdx
        RETURN fNodes[fIdx] AS n, 0 AS vRank, (fIdx + 1) AS fRank
    }
    
    // Aggregate results and calculate RRF score
    // Use max() to combine ranks if the node appeared in both searches
    WITH n, max(vRank) AS vectorRank, max(fRank) AS fulltextRank
    WITH n, vectorRank, fulltextRank,
         (CASE WHEN vectorRank > 0 THEN 1.0 / (60 + vectorRank) ELSE 0.0 END) +
         (CASE WHEN fulltextRank > 0 THEN 1.0 / (60 + fulltextRank) ELSE 0.0 END) AS rrfScore
    
    // Final Join and Return
    MATCH (n)-[:BELONGS_TO_PROJECT]->(p:Project)
    RETURN
        n.uid AS node_id,
        labels(n) AS labels,
        rrfScore,
        p.uid AS project_id,
        p.name AS project_name
    ORDER BY rrfScore DESC
    LIMIT $max_nodes
    """

    async with runtime.context.neo4j_driver.session() as session:
        kwargs = {
            'query_': query,
            'candidate_pool': CANDIDATE_POOL,
            'max_nodes': MAX_NODES,
        }
        result = await session.run(cypher, **kwargs)
        records = await result.values()

    # Post-process to aggregate evidence by project
    project_map: dict[str, ProjectMatch] = {}
    for node_uid, labels, score, project_id, project_name in records:
        evidence = Evidence(
            node_type=labels[0],
            focus=_labels_to_focus(labels),
            relevance_score=score
        )
        if project_id not in project_map:
            project_map[project_id] = ProjectMatch(
                project_id=project_id,
                project_name=project_name,
                evidence=[evidence]
            )
        # Only append evidence if we don't have enough already to keep the evidence list concise and relevant
        elif len(project_map[project_id].evidence) < MAX_EVIDENCE:
            project_map[project_id].evidence.append(evidence)

    # Return the top k projects sorted by relevance
    relevant_projects = sorted(list(project_map.values()), reverse=True)
    return relevant_projects[:MAX_PROJECTS]


def _build_project_query(focuses: Iterable[Focus]) -> str:
    """Generate a Cypher query to retrieve detailed information about a project."""
    focus_set: set[str] = set(focuses)
    query_parts: list[str] = []

    # Track which variables are currently in the Cypher scope
    # 'p' is our anchor project node
    scope = {"p"}

    def with_clause(extra: list[str] = None) -> str:
        """Helper to generate a WITH clause containing all active variables."""
        current_vars = sorted(list(scope))
        if extra:
            # Add temporary calculation variables to the projection
            return f"WITH {', '.join(current_vars + extra)}"
        return f"WITH {', '.join(current_vars)}"

    # --- BASE ---
    query_parts.append("MATCH (p:Project {uid: $project_id})")
    query_parts.append(with_clause())

    # --- RESULTS ---
    if "RESULTS" in focus_set:
        query_parts.append("""
    OPTIONAL MATCH (p)-[:LEAD_TO]->(o:Outcome)
    WITH p, [x IN collect(DISTINCT o.description) WHERE x IS NOT NULL] AS outcomes
    WITH p, CASE WHEN size(outcomes) > 0 THEN { outcomes: outcomes } ELSE NULL END AS results
        """)
        scope.add("results")

    # --- TECHNICAL ---
    if "TECHNICAL" in focus_set:
        # Components
        query_parts.append(f"OPTIONAL MATCH (p)-[:COMPOSED_OF]->(c:ArchitectureComponent)")
        query_parts.append(with_clause(["collect(DISTINCT {uid: c.uid, name: c.name, detail: c.detail}) AS raw_comps"]))

        # Technologies
        query_parts.append("""
    OPTIONAL MATCH (p)-[:COMPOSED_OF]->(c2:ArchitectureComponent)-[:IMPLEMENTED_WITH]->(t:Technology)
        """)
        query_parts.append(with_clause([
            "raw_comps AS components",
            "collect(DISTINCT {uid: t.uid, name: t.name, thoughts: t.thoughts}) AS technologies",
            "collect(DISTINCT {component_id: c2.uid, technology_id: t.uid}) AS tech_map"
        ]))

        # Skills
        query_parts.append("""
    OPTIONAL MATCH (p)-[:COMPOSED_OF]->(c3:ArchitectureComponent)-[:DEMONSTRATES]->(s:Skill)
        """)
        query_parts.append(with_clause([
            "components", "technologies", "tech_map",
            "collect(DISTINCT {uid: s.uid, name: s.name}) AS skills",
            "collect(DISTINCT {component_id: c3.uid, skill_id: s.uid}) AS skill_map"
        ]))

        # Package Technical
        query_parts.append(f"""
    {with_clause()} , {{
        components: [c IN components WHERE c.uid IS NOT NULL],
        technologies: [t IN technologies WHERE t.uid IS NOT NULL],
        skills: [s IN skills WHERE s.uid IS NOT NULL],
        component_tech_map: [m IN tech_map WHERE m.component_id IS NOT NULL],
        component_skill_map: [m IN skill_map WHERE m.component_id IS NOT NULL]
    }} AS technical
        """)
        scope.add("technical")

    # --- STRATEGIC ---
    if "STRATEGIC" in focus_set:
        # 1. Constraints
        query_parts.append("OPTIONAL MATCH (p)-[:ENCOUNTERED]->(con:Constraint)")
        query_parts.append(with_clause([
            "collect(DISTINCT {uid: con.uid, description: con.description}) AS raw_constraints"
        ]))

        # 2. Philosophies via Builders
        query_parts.append("""
        OPTIONAL MATCH (builder:Person)-[:BUILT]->(p)
        OPTIONAL MATCH (builder)-[:BELIEVES]->(phil:Philosophy)
            """)
        query_parts.append(with_clause([
            "raw_constraints",
            "collect(DISTINCT phil) AS phil_nodes",
            "collect(DISTINCT {uid: phil.uid, statement: phil.statement}) AS raw_phils"
        ]))

        # 3. Decisions & Mapping (This is where the bug lived)
        query_parts.append("""
        OPTIONAL MATCH (phil2:Philosophy)-[:GUIDED]->(d:Decision)
        WHERE phil2 IN phil_nodes 
          AND (
            EXISTS { (d)-[:ADDRESSED]->(:Constraint)<-[:ENCOUNTERED]-(p) } OR 
            EXISTS { (d)-[:SHAPED]->(:ArchitectureComponent)<-[:COMPOSED_OF]-(p) }
          )

        // Ensure we only collect constraints/components tied to THIS project
        OPTIONAL MATCH (d)-[:ADDRESSED]->(dc:Constraint) 
        WHERE (p)-[:ENCOUNTERED]->(dc)

        OPTIONAL MATCH (d)-[:SHAPED]->(dac:ArchitectureComponent)
        WHERE (p)-[:COMPOSED_OF]->(dac)
        """)

        # We MUST include d and phil2 here so they are available for the NEXT step
        query_parts.append(with_clause([
            "raw_constraints", "raw_phils", "d", "phil2",
            "collect(DISTINCT dc.uid) AS d_con_ids",
            "collect(DISTINCT dac.uid) AS d_comp_ids"
        ]))

        # 4. Final Aggregation for Strategic
        # Here we group by the project scope to turn individual 'd' rows into one list
        query_parts.append(f"""
        WITH {', '.join(sorted(list(scope)))},
             [c IN raw_constraints WHERE c.uid IS NOT NULL] AS constraints,
             [ph IN raw_phils WHERE ph.uid IS NOT NULL] AS philosophies,
             collect(DISTINCT {{
                description: d.description,
                reasoning: d.reasoning,
                tradeoff: d.tradeoff,
                addresses_constraint_ids: [x IN d_con_ids WHERE x IS NOT NULL],
                affects_component_ids: [x IN d_comp_ids WHERE x IS NOT NULL],
                guided_by_philosophy_ids: [phil2.uid]
             }}) AS raw_decisions

        WITH {', '.join(sorted(list(scope)))}, 
             {{
                constraints: constraints,
                philosophies: philosophies,
                decisions: [dec IN raw_decisions WHERE dec.description IS NOT NULL]
             }} AS strategic
            """)
        scope.add("strategic")

    # --- FINAL RETURN ---
    res_val = "results" if "results" in scope else "NULL"
    tech_val = "technical" if "technical" in scope else "NULL"
    strat_val = "strategic" if "strategic" in scope else "NULL"

    query_parts.append(f"""
    RETURN {{
        project_name: p.name,
        results: {res_val},
        technical: {tech_val},
        strategic: {strat_val}
    }} AS projectDetail
    """)

    return "\n".join(query_parts)


# noinspection PyIncorrectDocstring
@tool
async def get_project_detail(
    project_id: str,
    focus: list[Focus],
    runtime: ToolRuntime[AgentContext]
) -> ProjectDetail:
    """Retrieve detailed information about a specific project.

    Use this tool when you need comprehensive information about a project's technical
    implementation, strategic decisions, or results. Request only the aspects relevant
    to the user's question to keep responses focused and efficient.

    Args:
        project_id: The unique identifier of the project
        focus: List of aspects to retrieve. Choose from:
            - "RESULTS": Outcomes and tangible results of the project
            - "TECHNICAL": Architecture components, technologies used, and skills demonstrated
            - "STRATEGIC": Constraints faced and decisions made during development

    Returns:
        ProjectDetail with requested sections populated:
        - results.outcomes: List of project outcomes
        - technical.components: Architecture components with IDs for cross-referencing
        - technical.technologies: Tech stack with thoughts/context
        - technical.skills: Skills demonstrated by the project
        - technical.component_tech_map: Which technologies were used in which components
        - technical.component_skill_map: Which skills are demonstrated by which components
        - strategic.constraints: Challenges and limitations faced
        - strategic.decisions: Key choices made, including reasoning, tradeoffs,
          constraints addressed (by ID), and components affected (by ID)
    """
    if not focus:
        raise ValueError("Must specify at least one focus area")

    cypher = _build_project_query(focus)
    async with runtime.context.neo4j_driver.session() as session:
        result = await session.run(cypher, project_id=project_id)
        record = await result.single()

    if record is None:
        raise ValueError(f"Project {project_id} not found")
    return ProjectDetail(**record['projectDetail'])


Dimension = Literal['TECHNOLOGY', 'SKILL', 'PHILOSOPHY']
Role = Literal['LANGUAGE', 'FRAMEWORK', 'INFRASTRUCTURE', 'DATA', 'INTERFACE', 'DEVOPS']


# Gemini doesn't like literal ints, so we need to use a field
# https://github.com/pydantic/pydantic-ai/issues/1691
class GlobalPatternsInput(BaseModel):
    dimension: Dimension
    roles: list[Role] | None = None
    specificity: int | None = Field(None, ge=1, le=3)


# noinspection PyIncorrectDocstring
@tool(args_schema=GlobalPatternsInput)
async def summarise_global_patterns(
    dimension: Dimension,
    runtime: ToolRuntime[AgentContext],
    roles: list[Role] | None = None,
    specificity: int | None = None
) -> GlobalPatternSummary:
    """Analyse and aggregate recurring technologies, skills, or philosophies across projects.

    Returns the top 10 ranked patterns with supporting project evidence. Intended for answering
    cross-project and meta-level questions about trends and common practices.
    In general, only one of `roles` or `specificity` should be specified.

    Args:
        dimension: The global dimension to summarise
        roles (optional): Restrict TECHNOLOGY patterns to specific roles. Ignored for other
            dimensions.
        specificity (optional): Control abstraction level for TECHNOLOGY patterns (1 = high-level,
            3 = very specific). Ignored for other dimensions.

    Returns:
        A summary of global patterns in the specified dimension, including:
        - node_name: The name of the technology, skill, or philosophy
        - thoughts: Any associated thoughts or context (for technologies)
        - project_count: How many projects match this pattern
        - project_ids: Which projects match this pattern
        - evidence: For each matching project, which components are associated with the pattern
    """
    MAX_RESULTS = 10

    if dimension == 'TECHNOLOGY':
        conditions = []
        conditions_str = ''
        if roles:
            conditions.append(f"x.role IN {roles}")
        if specificity:
            conditions.append(f"x.specificity >= {specificity}")
        if conditions:
            conditions_str = f"WHERE {' AND '.join(conditions)}"

        pathway_clause = f"""
        MATCH (p:Project)-[:COMPOSED_OF]->(c:ArchitectureComponent)
        MATCH (c)-[:IMPLEMENTED_WITH]->(x:Technology)
        {conditions_str}
        """
        node_name = 'x.name'

    elif dimension == 'SKILL':
        pathway_clause = """
        MATCH (p:Project)-[:COMPOSED_OF]->(c:ArchitectureComponent)
        MATCH (c)-[:DEMONSTRATES]->(s:Skill)
        """
        node_name = 'x.name'

    elif dimension == 'PHILOSOPHY':
        pathway_clause = """
        MATCH (x:Philosophy)-[:GUIDED]->(d:Decision)
        MATCH (p:Project)
        WHERE (d)-[:ADDRESSED]->(:Constraint)<-[:ENCOUNTERED]-(p)
           OR (d)-[:SHAPED]->(:ArchitectureComponent)<-[:COMPOSED_OF]-(p)
        """
        node_name = 'x.statement'

    else:
        raise ValueError(f"Invalid dimension: {dimension}")

    cypher = f"""
    {pathway_clause}

    // Group components by project
    WITH x, p, collect(DISTINCT c.name) AS component_names

    // Collect into a list of project-keyed objects
    WITH x, 
         collect(DISTINCT p.uid) AS project_ids,
         collect({{ 
           project_id: p.uid, 
           components: component_names 
         }}) AS evidence

    RETURN
      {node_name} AS node_name,
      x.thoughts,  // may be null
      size(project_ids) AS project_count,
      project_ids,
      evidence
    ORDER BY project_count DESC
    LIMIT $max_results"""

    async with runtime.context.neo4j_driver.session() as session:
        result = await session.run(cypher, max_results=MAX_RESULTS)
        records = await result.values()

    # Cypher cannot produce records with dynamic keys, so we need to remap in Python
    patterns = []
    for name, thoughts, project_count, project_ids, evidence_collection in records:
        evidence = {e['project_id']: e['components'] for e in evidence_collection}
        patterns.append(Pattern(
            name=name,
            thoughts=thoughts,
            project_count=project_count,
            project_ids=project_ids,
            evidence=evidence
        ))

    return GlobalPatternSummary(
        dimension=dimension,
        patterns=patterns
    )
