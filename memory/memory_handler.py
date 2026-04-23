import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class ResourceMemory:
    def __init__(self, file_path: str = "memory.json"):
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
                if not isinstance(self.data, dict) or "users" not in self.data:
                    self.data = {"users": {}}

                # ✅ Migrate user structures
                for user_id, user_data in self.data["users"].items():
                    if not isinstance(user_data, dict):
                        self.data["users"][user_id] = {"resources": []}
                        continue

                    # Fix wrong key like "messages"
                    if "resources" not in user_data:
                        self.data["users"][user_id]["resources"] = []

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
            self.data["users"][user_id] = {"resources": []}

        # safety fix
        if "resources" not in self.data["users"][user_id]:
            self.data["users"][user_id]["resources"] = []

    def _find_index(self, user_id: str, resource_id: str) -> Optional[int]:
        resources = self.data["users"][user_id]["resources"]
        for i, r in enumerate(resources):
            if r.get("id") == resource_id:
                return i
        return None

    # -----------------------
    # Fetching
    # -----------------------
    def list(self, user_id: str, filters: Dict[str, Any] = None) -> List[Dict]:
        self._ensure_user(user_id)
        results = self.data["users"][user_id]["resources"]

        if not filters:
            return results

        def match(resource):
            for k, v in filters.items():
                keys = k.split(".")
                val = resource
                for key in keys:
                    val = val.get(key, None)
                    if val is None:
                        return False
                if val != v:
                    return False
            return True

        return [r for r in results if match(r)]

    def get(self, user_id: str, resource_id: str) -> Optional[Dict]:
        self._ensure_user(user_id)
        idx = self._find_index(user_id, resource_id)
        return None if idx is None else self.data["users"][user_id]["resources"][idx]

    def get_all(self, user_id: str) -> List[Dict]:
        self._ensure_user(user_id)
        return self.data["users"][user_id]["resources"]
    
    def get_by_type(self, user_id: str, type: str) -> List[Dict]:
        self._ensure_user(user_id)
        print("self.get_all(user_id)", self.get_all(user_id))
        return [r for r in self.get_all(user_id) if type in r.get("type", "") or r.get("type") == type]
    # -----------------------
    # Add / Merge
    # -----------------------
    def upsert(self, user_id: str, resources: List[Dict]) -> int:
        self._ensure_user(user_id)

        inserted = 0
        touched = 0

        for r in resources:
            if not isinstance(r, dict) or not r.get("id"):
                continue  # skip invalid entries

            idx = self._find_index(user_id, r["id"])

            if idx is None:
                r.setdefault("timestamps", {})
                r["timestamps"]["added_at"] = self._now()
                r["timestamps"]["updated_at"] = self._now()
                self.data["users"][user_id]["resources"].append(r)
                inserted += 1
                touched += 1
            else:
                existing = self.data["users"][user_id]["resources"][idx]

                r["timestamps"] = existing.get("timestamps", {})
                r["timestamps"]["updated_at"] = self._now()

                existing.update(r)
                touched += 1

        if touched:
            self._save()

        return inserted

    # -----------------------
    # Update
    # -----------------------
    def update_status(self, user_id: str, resource_id: str, status: str) -> bool:
        self._ensure_user(user_id)
        idx = self._find_index(user_id, resource_id)
        if idx is None:
            return False
        self.data["users"][user_id]["resources"][idx]["state"] = {"status": status}
        self._save()
        return True

    def update(self, user_id: str, resource_id: str, updates: Dict[str, Any]) -> bool:
        self._ensure_user(user_id)

        idx = self._find_index(user_id, resource_id)
        if idx is None:
            return False

        resource = self.data["users"][user_id]["resources"][idx]

        for k, v in updates.items():
            keys = k.split(".")
            target = resource
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            target[keys[-1]] = v

        resource.setdefault("timestamps", {})
        resource["timestamps"]["updated_at"] = self._now()

        self._save()
        return True

    # -----------------------
    # Bulk operations
    # -----------------------
    def bulk_update(self, user_id: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> int:
        matched = self.list(user_id, filters)
        count = 0

        for r in matched:
            if self.update(user_id, r.get("id"), updates):
                count += 1

        return count

    # -----------------------
    # State transitions
    # -----------------------
    def set_status(self, user_id: str, filters: Dict[str, Any], status: str) -> int:
        return self.bulk_update(user_id, filters, {"state.status": status})

    # -----------------------
    # Delete
    # -----------------------
    def delete(self, user_id: str, resource_id: str) -> bool:
        self._ensure_user(user_id)

        idx = self._find_index(user_id, resource_id)
        if idx is None:
            return False

        self.data["users"][user_id]["resources"].pop(idx)
        self._save()
        return True

    # -----------------------
    # Utility
    # -----------------------
    def clear(self, user_id: str):
        self.data["users"][user_id] = {"resources": []}
        self._save()


user_recommended_memory = ResourceMemory(file_path="Memory/user_recommendation_memory.json")