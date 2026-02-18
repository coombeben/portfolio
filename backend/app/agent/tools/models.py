"""
NB: Doing this with `neomodel` would be unbelievably inefficient as it has limited support
for dynamic queries (akin to sqlalchemy). Instead, we use raw Cypher queries and map the results
 to these Pydantic models.
"""
from functools import total_ordering
from typing import Literal

from pydantic import BaseModel, Field

__all__ = ['ProjectDetail', 'ProjectMatch']


Node = Literal['Person', 'Project', 'Outcome', 'Philosophy', 'Decision', 'ArchitectureComponent', 'Constraint',
'Technology', 'Skill']
Relationship = Literal['BUILT', 'BELIEVES', 'GUIDED', 'ENCOUNTERED', 'COMPOSED_OF', 'LEAD_TO', 'ADDRESSED', 'SHAPED',
'IMPLEMENTED_WITH', 'DEMONSTRATES']


# Output models
class Component(BaseModel):
    uid: str
    name: str
    detail: str


class Technology(BaseModel):
    uid: str
    name: str
    thoughts: str


class Skill(BaseModel):
    uid: str
    name: str


class Decision(BaseModel):
    description: str
    reasoning: str
    tradeoff: str
    addresses_constraint_ids: list[str]
    affects_component_ids: list[str]
    guided_by_philosophy_ids: list[str]


class Philosophy(BaseModel):
    uid: str
    statement: str


class Constraint(BaseModel):
    uid: str
    description: str


class SearchResult(BaseModel):
    node_type: Node
    uid: str
    metadata: dict
    parent_project: str
    relevance_score: float


class ComponentTechMap(BaseModel):
    component_id: str
    technology_id: str


class ComponentSkillMap(BaseModel):
    component_id: str
    skill_id: str


class Results(BaseModel):
    outcomes: list[str] = Field(default_factory=list)


class Technical(BaseModel):
    components: list[Component] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    component_tech_map: list[ComponentTechMap] = Field(default_factory=list)
    component_skill_map: list[ComponentSkillMap] = Field(default_factory=list)


class Strategic(BaseModel):
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
    node_type: Node
    focus: Literal['RESULTS', 'TECHNICAL', 'STRATEGIC'] | None
    relevance_score: float

    def __lt__(self, other):
        return self.relevance_score < other.relevance_score

    def __eq__(self, other):
        return self.relevance_score == other.relevance_score


@total_ordering
class ProjectMatch(BaseModel):
    """Output model of the search tool"""
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
