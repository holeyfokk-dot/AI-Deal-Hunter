from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AgentMetadata:
    name: str
    version: str
    author: str
    description: str
    capabilities: List[str]
    priority: int = 0
    enabled: bool = True
    required_tools: List[str] = field(default_factory=list)


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: List[BaseAgent] = []

    def register_agent(self, agent_cls: type[BaseAgent]) -> None:
        if not issubclass(agent_cls, BaseAgent):
            return

        if getattr(agent_cls, "__abstractmethods__", False):
            return

        if any(type(agent) is agent_cls for agent in self._agents):
            return

        self._agents.append(agent_cls())

    def get_agents(self) -> List[BaseAgent]:
        return list(self._agents)


DEFAULT_AGENT_REGISTRY = AgentRegistry()


class BaseAgent(ABC):
    metadata: AgentMetadata

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if getattr(cls, "__abstractmethods__", False):
            return

        DEFAULT_AGENT_REGISTRY.register_agent(cls)

    @classmethod
    @abstractmethod
    def create_metadata(cls) -> AgentMetadata:
        raise NotImplementedError

    def __init__(self) -> None:
        self.metadata = self.create_metadata()

    @abstractmethod
    def can_handle(self, capability: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": True,
            "details": "Agent loaded successfully.",
        }

    @classmethod
    def register(cls, registry: AgentRegistry) -> None:
        registry.register_agent(cls)
