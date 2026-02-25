"""
This module defines the Pydantic models for the outputs of the various tools used by the agent.

NB: Doing this with `neomodel` would be unbelievably inefficient as it has limited support
for dynamic queries (akin to sqlalchemy). Instead, we use raw Cypher queries and map the results
 to these Pydantic models.
"""
from functools import total_ordering
from typing import Literal

from pydantic import BaseModel, Field

__all__ = ['ProjectDetail', 'Evidence', 'ProjectMatch', 'Pattern', 'GlobalPatternSummary']


Node = Literal['Person', 'Project', 'Outcome', 'Philosophy', 'Decision', 'ArchitectureComponent',
'Constraint', 'Technology', 'Skill']
Relationship = Literal['BUILT', 'BELIEVES', 'GUIDED', 'ENCOUNTERED', 'COMPOSED_OF', 'LEAD_TO',
'ADDRESSED', 'SHAPED', 'IMPLEMENTED_WITH', 'DEMONSTRATES']


# Output models
class Component(BaseModel):
    """Model for an architecture component node."""
    uid: str
    name: str
    detail: str


class Technology(BaseModel):
    """Model for a technology node."""
    uid: str
    name: str
    thoughts: str


class Skill(BaseModel):
    """Model for a skill node."""
    uid: str
    name: str


class Decision(BaseModel):
    """Model for a decision node."""
    description: str
    reasoning: str
    tradeoff: str
    addresses_constraint_ids: list[str]
    affects_component_ids: list[str]
    guided_by_philosophy_ids: list[str]


class Philosophy(BaseModel):
    """Model for a philosophy node."""
    uid: str
    statement: str


class Constraint(BaseModel):
    """Model for a constraint node."""
    uid: str
    description: str


class Outcome(BaseModel):
    """Model for an outcome node."""
    description: str
    type: Literal['result', 'learning', 'reflection']


class ComponentTechMap(BaseModel):
    """Mapping model to link architecture components to technologies."""
    component_id: str
    technology_id: str


class ComponentSkillMap(BaseModel):
    """Mapping model to link architecture components to skills."""
    component_id: str
    skill_id: str


class Results(BaseModel):
    """Output model for results focus"""
    outcomes: list[Outcome] = Field(default_factory=list)


class Technical(BaseModel):
    """Output model for technical focus"""
    components: list[Component] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    component_tech_map: list[ComponentTechMap] = Field(default_factory=list)
    component_skill_map: list[ComponentSkillMap] = Field(default_factory=list)


class Strategic(BaseModel):
    """Output model for strategic focus"""
    constraints: list[Constraint] = Field(default_factory=list)
    philosophies: list[Philosophy] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)


class ProjectDetail(BaseModel):
    """Output model for the project detail tool."""
    project_name: str

    # For RESULTS focus
    results: Results | None = None
    # For TECHNICAL focus
    technical: Technical | None = None
    # For STRATEGIC focus
    strategic: Strategic | None = None


@total_ordering
class Evidence(BaseModel):
    """Model for evidence of a project matching a query"""
    node_type: Node
    focus: Literal['RESULTS', 'TECHNICAL', 'STRATEGIC'] | None
    relevance_score: float

    def __lt__(self, other):
        return self.relevance_score < other.relevance_score

    def __eq__(self, other):
        return self.relevance_score == other.relevance_score


@total_ordering
class ProjectMatch(BaseModel):
    """Output model of the `search_knowledge_base` tool"""
    project_id: str
    project_name: str
    evidence: list[Evidence] = Field(default_factory=list)

    @property
    def relevance_score(self) -> float:
        if not self.evidence:
            return 0.
        return sum(evidence.relevance_score for evidence in self.evidence)

    def __lt__(self, other):
        return self.relevance_score < other.relevance_score

    def __eq__(self, other):
        return self.relevance_score == other.relevance_score


class Pattern(BaseModel):
    """Model for a pattern of skills/technologies/philosophies used across multiple projects"""
    name: str
    thoughts: str | None = None
    project_count: int
    project_ids: list[str]
    evidence: dict[str, list[str]]  # {project_id: [*evidence]}


class GlobalPatternSummary(BaseModel):
    """Output model of the `summarise_global_patterns` tool"""
    dimension: str
    patterns: list[Pattern]
