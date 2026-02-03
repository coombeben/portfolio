import os
from functools import cache
from typing import Literal

from pydantic import BaseModel, Field
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
    neo4j_uri: str = os.environ.get('NEO4J_URI')
    neo4j_auth: tuple[str, str] = tuple(os.environ.get('NEO4J_AUTH').split('/', 1))
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
