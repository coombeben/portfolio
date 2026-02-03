import os
from functools import cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from langchain.chat_models import  init_chat_model, BaseChatModel

__all__ = ['Config', 'get_config']


class LLMConfig(BaseModel):
    provider: str
    name: str
    kwargs: dict = Field(default_factory=dict)

    def to_chat_model(self) -> BaseChatModel:
        """Returns the LangChain chat model instance."""
        return init_chat_model(self.name, model_provider=self.provider, **self.kwargs)


class Config(BaseSettings):
    neo4j_uri: str = Field(env='NEO4J_URI')
    neo4j_auth: tuple[str, str] | None = Field(None, env='NEO4J_AUTH')
    enable_moderation: bool = True

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

    @field_validator('neo4j_auth', mode='before')
    def _parse_neo4j_auth(cls, v: str | None) -> tuple[str, str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            parts = v.split('/', 1)
            if len(parts) != 2:
                raise ValueError('NEO4J_AUTH must be in the form username/password')
            return parts[0], parts[1]
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return v[0], v[1]
        raise TypeError('Invalid type for NEO4J_AUTH')


class DevelopmentConfig(Config):
    neo4j_uri: str = 'neo4j://localhost:7687'
    enable_moderation: bool = False


class ProductionConfig(Config):
    pass


ConfigType = Literal['development', 'production']


@cache
def get_config(config_type: ConfigType) -> Config:
    """Returns the configuration object based on the environment."""
    if config_type == 'development':
        return DevelopmentConfig()

    return ProductionConfig()
