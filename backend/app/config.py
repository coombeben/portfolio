"""
Configuration management for the application.
"""
from functools import cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain.chat_models import init_chat_model, BaseChatModel

from app.projector import ProjectionConfig


__all__ = ['Config', 'settings']

Environment = Literal['development', 'production']


class LLMConfig(BaseModel):
    """Configuration for LLMs."""
    provider: str
    name: str
    kwargs: dict = Field(default_factory=dict)

    def to_chat_model(self) -> BaseChatModel:
        """Returns the LangChain chat model instance."""
        return init_chat_model(self.name, model_provider=self.provider, **self.kwargs)


class Config(BaseSettings):
    """Application configuration."""
    environment: Environment = 'production'

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    redis_uri: str
    redis_password: str

    external_domain: str = Field(validation_alias='NEXT_PUBLIC_BASE_URL')
    app_password: str
    secret_key: str

    # TTL configurations
    session_ttl: int = 60 * 60 * 24 * 7  # 1 week
    checkpoint_ttl: dict = {
        "default_ttl": 60 * 24 * 7,  # 1 week (`AsyncRedisSaver` uses minutes, not seconds)
        "refresh_on_read": True
    }

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

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_ignore_empty=True,
        extra='ignore'
    )


class DevelopmentConfig(Config):
    """Development configuration."""
    environment: Environment = 'development'
    daily_limit: int = 1000


class ProductionConfig(Config):
    """Production configuration."""
    # Redact sensitive content for prod
    projection_config: ProjectionConfig = ProjectionConfig(
        exclude_nodes={"moderator"},
        redact_tool_results={"get_project_detail"},
    )


@cache
def get_config(environment: Environment = 'production') -> Config:
    """Returns the configuration object based on the environment."""
    if environment == 'development':
        return DevelopmentConfig()

    return ProductionConfig()


settings = get_config('production')
