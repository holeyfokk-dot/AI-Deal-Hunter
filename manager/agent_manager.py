from __future__ import annotations

import importlib
import pkgutil
import sys
import time
from typing import Any, Dict, List, Optional

import agents
from agents.base_agent import AgentRegistry, BaseAgent, DEFAULT_AGENT_REGISTRY
from config import DEBUG_MODE, logger

FRAMEWORK_VERSION = "1.0.0"
START_TIME = time.monotonic()


class AgentManager:
    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self.registry = registry or DEFAULT_AGENT_REGISTRY
        self._discover_specialists()

    def _discover_specialists(self) -> None:
        for finder, module_name, is_package in pkgutil.iter_modules(agents.__path__):
            if module_name.startswith("_"):
                continue

            importlib.import_module(f"{agents.__name__}.{module_name}")

    def get_specialists(self) -> List[BaseAgent]:
        return [agent for agent in self.registry.get_agents() if agent.metadata.enabled]

    def get_specialist(self, name: str) -> Optional[Dict[str, Any]]:
        for agent in self.registry.get_agents():
            if agent.metadata.name.lower() == name.lower():
                metadata = agent.metadata
                health = agent.health_check()
                return {
                    "name": metadata.name,
                    "version": metadata.version,
                    "author": metadata.author,
                    "description": metadata.description,
                    "capabilities": metadata.capabilities,
                    "priority": metadata.priority,
                    "enabled": metadata.enabled,
                    "required_tools": metadata.required_tools,
                    "health": health,
                }

        return None

    def list_specialists(self) -> List[Dict[str, Any]]:
        specialists = []

        for agent in self.registry.get_agents():
            metadata = agent.metadata
            health = agent.health_check()

            specialists.append({
                "name": metadata.name,
                "version": metadata.version,
                "author": metadata.author,
                "description": metadata.description,
                "capabilities": metadata.capabilities,
                "priority": metadata.priority,
                "enabled": metadata.enabled,
                "required_tools": metadata.required_tools,
                "health": health,
            })

        return sorted(specialists, key=lambda item: item["name"])

    def startup_summary(self) -> None:
        specialists = self.list_specialists()
        count = len(specialists)
        logger.info("Loaded %d specialists successfully.", count)

        if not DEBUG_MODE:
            return

        for specialist in specialists:
            health = specialist["health"]
            logger.debug("Specialist: %s", specialist["name"])
            logger.debug("  Version: %s", specialist["version"])
            logger.debug("  Author: %s", specialist["author"])
            logger.debug("  Description: %s", specialist["description"])
            logger.debug("  Priority: %s", specialist["priority"])
            logger.debug("  Enabled: %s", specialist["enabled"])
            logger.debug("  Capabilities: %s", specialist["capabilities"])
            logger.debug("  Required Tools: %s", specialist["required_tools"])
            logger.debug("  Health Status: %s", health)

    def find_specialists(self, capability: str) -> List[BaseAgent]:
        specialists = [
            agent
            for agent in self.get_specialists()
            if agent.can_handle(capability)
        ]

        return sorted(specialists, key=lambda agent: agent.metadata.priority, reverse=True)

    def route(self, capability: str, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        specialists = self.find_specialists(capability)

        responses: List[Dict[str, Any]] = []

        for specialist in specialists:
            response = specialist.handle(request)
            responses.append({
                "agent": specialist.metadata.name,
                "response": self._serialize_response(response),
            })

        return responses

    def collaborate(self, capabilities: List[str], request: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        for capability in capabilities:
            results[capability] = self.route(capability, request)

        return results

    def _serialize_response(self, response: Any) -> Any:
        if hasattr(response, "to_dict"):
            return response.to_dict()

        if isinstance(response, dict):
            return {key: self._serialize_response(value) for key, value in response.items()}

        if isinstance(response, list):
            return [self._serialize_response(item) for item in response]

        if hasattr(response, "value"):
            return response.value

        return response

    def get_system_status(self) -> Dict[str, Any]:
        all_specialists = self.registry.get_agents()
        enabled = [agent for agent in all_specialists if agent.metadata.enabled]
        disabled = [agent for agent in all_specialists if not agent.metadata.enabled]
        loaded_tools = sorted({tool for agent in all_specialists for tool in agent.metadata.required_tools})
        health_summary = self._build_health_summary(all_specialists)

        return {
            "framework_version": FRAMEWORK_VERSION,
            "loaded_specialist_count": len(all_specialists),
            "enabled_specialist_count": len(enabled),
            "disabled_specialist_count": len(disabled),
            "loaded_tools": loaded_tools,
            "memory_status": self._get_memory_status(),
            "uptime_seconds": time.monotonic() - START_TIME,
            "health_summary": health_summary,
        }

    def reload_specialist(self, name: str) -> bool:
        specialist = None
        module_name = None

        for agent in self.registry.get_agents():
            if agent.metadata.name.lower() == name.lower():
                specialist = agent
                module_name = type(agent).__module__
                break

        if specialist is None or module_name is None:
            logger.warning("Specialist '%s' not found for reload.", name)
            return False

        self.registry.remove_agent_by_name(specialist.metadata.name)

        if module_name not in sys.modules:
            logger.warning("Specialist module '%s' not loaded. Cannot reload.", module_name)
            return False

        try:
            module = sys.modules[module_name]
            importlib.reload(module)
            logger.info("Reloaded specialist '%s' successfully.", name)
            return True
        except Exception as exc:
            logger.error("Failed to reload specialist '%s': %s", name, exc)
            return False

    def _build_health_summary(self, agents_list: List[BaseAgent]) -> Dict[str, Any]:
        healthy = 0
        unhealthy = 0
        details: List[Dict[str, Any]] = []

        for agent in agents_list:
            result = agent.health_check()
            status = bool(result.get("healthy", False))

            if status:
                healthy += 1
            else:
                unhealthy += 1

            details.append({
                "name": agent.metadata.name,
                "healthy": status,
                "details": result.get("details"),
            })

        return {
            "healthy_specialists": healthy,
            "unhealthy_specialists": unhealthy,
            "details": details,
        }

    def _get_memory_status(self) -> Dict[str, Any]:
        memory_status: Dict[str, Any] = {
            "rss": None,
            "vms": None,
            "percent": None,
        }

        try:
            import psutil

            process = psutil.Process()
            info = process.memory_info()
            memory_status["rss"] = info.rss
            memory_status["vms"] = info.vms
            memory_status["percent"] = process.memory_percent()
        except ImportError:
            try:
                import resource

                usage = resource.getrusage(resource.RUSAGE_SELF)
                memory_status["rss"] = usage.ru_maxrss
            except Exception:
                memory_status = {"rss": None, "vms": None, "percent": None}
        except Exception:
            memory_status = {"rss": None, "vms": None, "percent": None}

        return memory_status
