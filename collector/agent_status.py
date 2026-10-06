from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any


SUCCESS_FRESHNESS = timedelta(hours=1)
VALID_EVENT_STATUSES = {"working", "success", "failure"}


class AgentStoreError(ValueError):
    pass


class AgentNotFoundError(AgentStoreError):
    pass


class StaleAgentEventError(AgentStoreError):
    pass


class AgentStore:
    def __init__(self, registry_path: Path, status_path: Path, projects_root: Path):
        self.registry_path = Path(registry_path)
        self.status_path = Path(status_path)
        self.projects_root = Path(projects_root).resolve()
        self._lock = RLock()

    def list_agents(self, now: datetime | None = None) -> dict[str, Any]:
        with self._lock:
            registry = self._read_registry()
            state = self._read_state()
            agents = [self._agent_view(agent, state["agents"].get(agent["id"]), now) for agent in registry["agents"]]
        counts = {status: 0 for status in ("working", "success", "failure", "needs_work")}
        for agent in agents:
            counts[agent["display_status"]] += 1
        return {"agents": agents, "counts": counts, "success_fresh_minutes": 60}

    def create_agent(self, name: str, project_path: str) -> dict[str, Any]:
        with self._lock:
            registry = self._read_registry()
            clean_name = self._validate_name(name)
            clean_path = self._validate_project_path(project_path)
            self._require_unique_path(registry, clean_path)
            agent_id = self._next_id(registry, clean_name)
            agent = {"id": agent_id, "name": clean_name, "project_path": clean_path}
            registry["agents"].append(agent)
            self._write_json(self.registry_path, registry)
            return self._agent_view(agent, None)

    def update_agent(self, agent_id: str, name: str, project_path: str) -> dict[str, Any]:
        with self._lock:
            registry = self._read_registry()
            agent = self._find_agent(registry, agent_id)
            clean_name = self._validate_name(name)
            clean_path = self._validate_project_path(project_path)
            self._require_unique_path(registry, clean_path, exclude_id=agent_id)
            agent.update({"name": clean_name, "project_path": clean_path})
            self._write_json(self.registry_path, registry)
            state = self._read_state()["agents"].get(agent_id)
            return self._agent_view(agent, state)

    def delete_agent(self, agent_id: str) -> None:
        with self._lock:
            registry = self._read_registry()
            self._find_agent(registry, agent_id)
            registry["agents"] = [agent for agent in registry["agents"] if agent["id"] != agent_id]
            state = self._read_state()
            state["agents"].pop(agent_id, None)
            self._write_json(self.registry_path, registry)
            self._write_json(self.status_path, state)

    def record_event(
        self,
        agent_id: str,
        status: str,
        job_id: str | None = None,
        message: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if status not in VALID_EVENT_STATUSES:
            raise AgentStoreError("Invalid agent status")
        clean_job_id = self._optional_text(job_id, "job_id", 120)
        clean_message = self._optional_text(message, "message", 500)
        event_time = self._as_utc(now or datetime.now(timezone.utc))
        with self._lock:
            registry = self._read_registry()
            agent = self._find_agent(registry, agent_id)
            state = self._read_state()
            current = state["agents"].get(agent_id, {})
            current_job = current.get("job_id")
            if status != "working" and current.get("status") == "working" and current_job and clean_job_id != current_job:
                raise StaleAgentEventError("Completion job_id does not match the active job")
            state["agents"][agent_id] = {
                "status": status,
                "job_id": clean_job_id,
                "message": clean_message,
                "updated_at": event_time.isoformat(timespec="seconds"),
            }
            self._write_json(self.status_path, state)
            return self._agent_view(agent, state["agents"][agent_id], event_time)

    def _read_registry(self) -> dict[str, Any]:
        payload = self._read_json(self.registry_path, {"version": 1, "agents": []})
        if payload.get("version") != 1 or not isinstance(payload.get("agents"), list):
            raise AgentStoreError("Agent registry must contain version 1 and an agents list")
        ids: set[str] = set()
        paths: set[str] = set()
        for raw in payload["agents"]:
            if not isinstance(raw, dict):
                raise AgentStoreError("Each agent registration must be an object")
            agent_id = str(raw.get("id", ""))
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", agent_id) or agent_id in ids:
                raise AgentStoreError("Agent IDs must be unique lowercase slugs")
            raw["name"] = self._validate_name(str(raw.get("name", "")))
            raw["project_path"] = self._validate_project_path(str(raw.get("project_path", "")))
            if raw["project_path"].casefold() in paths:
                raise AgentStoreError("Agent project paths must be unique")
            ids.add(agent_id)
            paths.add(raw["project_path"].casefold())
        return payload

    def _read_state(self) -> dict[str, Any]:
        payload = self._read_json(self.status_path, {"version": 1, "agents": {}})
        if payload.get("version") != 1 or not isinstance(payload.get("agents"), dict):
            raise AgentStoreError("Agent state must contain version 1 and an agents object")
        return payload

    @staticmethod
    def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentStoreError(f"Could not read {path.name}") from exc
        if not isinstance(payload, dict):
            raise AgentStoreError(f"{path.name} must contain a JSON object")
        return payload

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        temp_name = ""
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
                temp_name = handle.name
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and Path(temp_name).exists():
                Path(temp_name).unlink()

    def _validate_project_path(self, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        pure_path = PurePosixPath(normalized)
        if not normalized or pure_path.is_absolute() or re.match(r"^[A-Za-z]:/", normalized) or ".." in pure_path.parts or "." in pure_path.parts:
            raise AgentStoreError("project_path must be a relative path inside Projects")
        candidate = self.projects_root.joinpath(*pure_path.parts).resolve()
        try:
            candidate.relative_to(self.projects_root)
        except ValueError as exc:
            raise AgentStoreError("project_path must stay inside Projects") from exc
        if not candidate.is_dir():
            raise AgentStoreError("project_path must identify an existing project directory")
        return pure_path.as_posix()

    @staticmethod
    def _validate_name(value: str) -> str:
        clean = " ".join(value.split())
        if not clean or len(clean) > 100:
            raise AgentStoreError("name must contain 1 to 100 characters")
        return clean

    @staticmethod
    def _optional_text(value: str | None, field: str, max_length: int) -> str | None:
        if value is None:
            return None
        clean = " ".join(value.split())
        if not clean:
            return None
        if len(clean) > max_length:
            raise AgentStoreError(f"{field} is too long")
        return clean

    @staticmethod
    def _find_agent(registry: dict[str, Any], agent_id: str) -> dict[str, Any]:
        agent = next((entry for entry in registry["agents"] if entry["id"] == agent_id), None)
        if agent is None:
            raise AgentNotFoundError("Agent not found")
        return agent

    @staticmethod
    def _require_unique_path(registry: dict[str, Any], project_path: str, exclude_id: str | None = None) -> None:
        for agent in registry["agents"]:
            if agent["id"] != exclude_id and agent["project_path"].casefold() == project_path.casefold():
                raise AgentStoreError("An agent already uses this project path")

    @staticmethod
    def _next_id(registry: dict[str, Any], name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "agent"
        existing = {agent["id"] for agent in registry["agents"]}
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    @classmethod
    def _agent_view(
        cls,
        agent: dict[str, Any],
        state: dict[str, Any] | None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        current_time = cls._as_utc(now or datetime.now(timezone.utc))
        stored_status = state.get("status") if state else None
        updated_at = state.get("updated_at") if state else None
        display_status = stored_status or "needs_work"
        if stored_status == "success":
            try:
                updated = cls._as_utc(datetime.fromisoformat(updated_at))
            except (TypeError, ValueError):
                display_status = "needs_work"
            else:
                if current_time - updated >= SUCCESS_FRESHNESS:
                    display_status = "needs_work"
        if display_status not in {"working", "success", "failure", "needs_work"}:
            display_status = "needs_work"
        return {
            **agent,
            "last_status": stored_status,
            "display_status": display_status,
            "job_id": state.get("job_id") if state else None,
            "message": state.get("message") if state else None,
            "updated_at": updated_at,
        }

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
