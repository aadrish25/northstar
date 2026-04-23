import json
import os
from typing import List, Dict
from datetime import datetime


class ChatMemory:
    def __init__(self, file_path: str = "chat_memory.json", max_messages: int = 100):
        self.file_path = file_path
        self.max_messages = max_messages
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

                # ✅ FIX: ensure structure
                if "users" not in self.data:
                    self.data = {"users": {}}

            except:
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
        if "users" not in self.data:
            self.data["users"] = {}

        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {"messages": []}

    def _trim(self, user_id: str):
        msgs = self.data["users"][user_id]["messages"]
        if len(msgs) > self.max_messages:
            self.data["users"][user_id]["messages"] = msgs[-self.max_messages:]

    # -----------------------
    # Core Methods
    # -----------------------
    def add_user(self, user_id: str, text: str):
        self._ensure_user(user_id)
        self.data["users"][user_id]["messages"].append({
            "role": "user",
            "content": text,
            "timestamp": self._now()
        })
        self._trim(user_id)
        self._save()

    def add_agent(self, user_id: str, text: str):
        self._ensure_user(user_id)
        self.data["users"][user_id]["messages"].append({
            "role": "agent",
            "content": text,
            "timestamp": self._now()
        })
        self._trim(user_id)
        self._save()

    def add(self, user_id: str, role: str, text: str):
        """Generic add (if you want flexibility later)"""
        self._ensure_user(user_id)
        self.data["users"][user_id]["messages"].append({
            "role": role,
            "content": text,
            "timestamp": self._now()
        })
        self._trim(user_id)
        self._save()

    # -----------------------
    # Fetching
    # -----------------------
    def get_all(self, user_id: str) -> List[Dict]:
        self._ensure_user(user_id)
        return self.data["users"][user_id]["messages"]

    def get_recent(self, user_id: str, n: int = 10) -> List[Dict]:
        self._ensure_user(user_id)
        return self.data["users"][user_id]["messages"][-n:]

    def get_formatted(self, user_id: str, n: int = 10) -> str:
        """
        Returns formatted string for LLM prompt
        """
        msgs = self.get_recent(user_id, n)
        return "\n".join([
            f"{m['role']}: {m['content']}" for m in msgs
        ])

    # -----------------------
    # Utility
    # -----------------------
    def clear(self, user_id: str):
        self.data["users"][user_id] = {"messages": []}
        self._save()


chat_memory = ChatMemory()