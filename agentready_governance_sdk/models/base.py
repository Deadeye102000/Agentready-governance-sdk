"""Base model configuration for AgentReady Governance SDK."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseApiModel(BaseModel):
    """Base model with camelCase alias generation and populate_by_name."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
