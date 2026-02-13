from functools import cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from langchain.chat_models import init_chat_model, BaseChatModel
from neo4j import AsyncDriver

from app.projector import ProjectionConfig


__all__ = ['Config', 'settings', 'AgentContext']


class LLMConfig(BaseModel):
    provider: str
    name: str
    kwargs: dict = Field(default_factory=dict)

    def to_chat_model(self) -> BaseChatModel:
        """Returns the LangChain chat model instance."""
        return init_chat_model(self.name, model_provider=self.provider, **self.kwargs)


class Config(BaseSettings):
    neo4j_uri: str = Field(env='NEO4J_URI')
    neo4j_user: str = Field(env='NEO4J_USER')
    neo4j_password: str = Field('', env='NEO4J_PASSWORD')

    postgres_uri: str = Field(env='POSTGRES_URI')
    postgres_user: str = Field(env='POSTGRES_USER')
    postgres_password: str = Field(env='POSTGRES_PASSWORD')
    postgres_db: str = Field(env='POSTGRES_DB')

    enable_moderation: bool = True

    # Rate limiting
    # Max sessions per IP
    max_sessions: int = 3
    # Max messages per session
    daily_limit: int = 10

    # LLM options
    moderator_llm: LLMConfig = LLMConfig(
        provider='google_genai',
        name='gemini-flash-lite-latest',
        kwargs={'temperature': 0.},
    )
    chat_llm: LLMConfig = LLMConfig(
        provider='google_genai',
        name='gemini-3-flash-preview',
        kwargs={'thinking_level': 'low'}
    )

    # Content redaction
    projection_config: ProjectionConfig = Field(default_factory=ProjectionConfig)


class DevelopmentConfig(Config):
    enable_moderation: bool = False
    daily_limit: int = 1000


class ProductionConfig(Config):
    # Redact sensitive content for prod
    projection_config: ProjectionConfig = ProjectionConfig(
        exclude_nodes={"moderator"},
        redact_tool_args={"execute_cypher": {"cypher"}},
        redact_tool_results={"execute_cypher"},
    )


ConfigType = Literal['development', 'production']


@cache
def get_config(config_type: ConfigType = 'production') -> Config:
    """Returns the configuration object based on the environment."""
    if config_type == 'development':
        return DevelopmentConfig()

    return ProductionConfig()


settings = get_config('production')


class AgentContext(BaseModel):
    """Runtime context passed to LangGraph nodes and tools.

    Contains only what the agent needs during execution.
    Infrastructure concerns (checkpointer, connection strings) are not included.
    """
    model_config = {'arbitrary_types_allowed': True}

    # What nodes need
    moderator_llm: LLMConfig
    chat_llm: LLMConfig
    enable_moderation: bool

    # What tools need
    neo4j_driver: 'AsyncDriver'
