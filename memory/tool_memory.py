import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class ToolCacheMemory:
    def __init__(self, file_path: str = "tool_cache.json"):
        self.file_path = file_path
        self.data = {"users": {}}
        self._load()

    # -----------------------
    # Internal
    # -----------------------
    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    self.data = json.load(f)

                # ✅ Ensure root structure
                if not isinstance(self.data, dict):
                    self.data = {"users": {}}

                if "users" not in self.data or not isinstance(self.data["users"], dict):
                    self.data["users"] = {}

                # ✅ Fix per-user structure
                for user_id, user_data in list(self.data["users"].items()):
                    if not isinstance(user_data, dict):
                        self.data["users"][user_id] = {"cache": {}}
                        continue

                    if "cache" not in user_data or not isinstance(user_data["cache"], dict):
                        self.data["users"][user_id]["cache"] = {}

            except Exception:
                self.data = {"users": {}}
        else:
            self.data = {"users": {}}
            self._save()

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def _now(self):
        return datetime.utcnow().isoformat()

    def _ensure_user(self, user_id: str):
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"cache": {}}

        if "cache" not in self.data["users"][user_id]:
            self.data["users"][user_id]["cache"] = {}

        if not isinstance(self.data["users"][user_id]["cache"], dict):
            self.data["users"][user_id]["cache"] = {}

    def _ensure_entry(self, user_id: str, tool_id: str):
        """Ensure cache entry is valid dict"""
        cache = self.data["users"][user_id]["cache"]

        if tool_id in cache and not isinstance(cache[tool_id], dict):
            cache[tool_id] = {}

    # -----------------------
    # Core Methods
    # -----------------------
    def set(self, user_id: str, tool_id: str, result: Any, meta: Optional[Dict] = None):
        self._ensure_user(user_id)

        self.data["users"][user_id]["cache"][tool_id] = {
            "result": result,
            "timestamp": self._now(),
            "meta": meta or {}
        }

        self._save()

    def get(self, user_id: str, tool_id: str) -> Optional[Any]:
        self._ensure_user(user_id)

        entry = self.data["users"][user_id]["cache"].get(tool_id)

        if not isinstance(entry, dict):
            return None

        return entry.get("result")

    def get_full(self, user_id: str, tool_id: str) -> Optional[Dict]:
        self._ensure_user(user_id)

        entry = self.data["users"][user_id]["cache"].get(tool_id)

        if not isinstance(entry, dict):
            return None

        return entry

    def exists(self, user_id: str, tool_id: str) -> bool:
        self._ensure_user(user_id)
        return tool_id in self.data["users"][user_id]["cache"]

    # -----------------------
    # Update / Modify
    # -----------------------
    def update_meta(self, user_id: str, tool_id: str, meta_updates: Dict):
        self._ensure_user(user_id)

        entry = self.get_full(user_id, tool_id)
        if not entry:
            return False

        entry.setdefault("meta", {})
        entry["meta"].update(meta_updates)

        self._save()
        return True

    def delete(self, user_id: str, tool_id: str) -> bool:
        self._ensure_user(user_id)

        if tool_id not in self.data["users"][user_id]["cache"]:
            return False

        del self.data["users"][user_id]["cache"][tool_id]
        self._save()
        return True

    # -----------------------
    # Bulk / Utility
    # -----------------------
    def clear(self, user_id: str):
        self.data["users"][user_id] = {"cache": {}}
        self._save()

    def list_keys(self, user_id: str):
        self._ensure_user(user_id)
        return list(self.data["users"][user_id]["cache"].keys())

    def get_all(self, user_id: str):
        self._ensure_user(user_id)
        return self.data["users"][user_id]["cache"]

    # -----------------------
    # TTL support
    # -----------------------
    def is_expired(self, user_id: str, tool_id: str, ttl_seconds: int) -> bool:
        self._ensure_user(user_id)

        entry = self.get_full(user_id, tool_id)
        if not entry:
            return True

        try:
            ts = datetime.fromisoformat(entry.get("timestamp"))
        except Exception:
            return True

        delta = datetime.utcnow() - ts
        return delta.total_seconds() > ttl_seconds


tool_cache = ToolCacheMemory()