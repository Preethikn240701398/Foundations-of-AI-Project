"""
Database layer (Step 8 - storage).

* Uses MongoDB through Motor when it is reachable.
* Falls back to an in-memory store that is snapshotted to data/memory_db.json, so the project
  still runs (and keeps its data between restarts) on a laptop without MongoDB installed.
Both back-ends expose the same small async API, so routers never care which one is active.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId, json_util
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings

COLLECTIONS = ["users", "profiles", "foods", "meals", "workouts", "logs", "chat_history",
               "diet_plans", "diary", "weights", "meta"]


def utcnow():
    return datetime.now(timezone.utc)


def oid(value: str | None = None):
    return ObjectId(value) if value else ObjectId()


def serialize(doc: dict | None) -> dict | None:
    """Convert a Mongo document into JSON-friendly data."""
    if not doc:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for key, value in list(out.items()):
        if isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
    return out


# ---------------------------------------------------------------------------
# In-memory collection (same API surface as Motor for the calls we use)
# ---------------------------------------------------------------------------
def _match(doc: dict, query: dict) -> bool:
    for k, v in query.items():
        if k == "$or":
            if not any(_match(doc, q) for q in v):
                return False
            continue
        dv = doc.get(k)
        if isinstance(v, dict) and any(op.startswith("$") for op in v):
            if "$in" in v:
                pool = v["$in"]
                hit = any(x in pool for x in dv) if isinstance(dv, list) else dv in pool
                if not hit:
                    return False
            if "$ne" in v and dv == v["$ne"]:
                return False
            if "$gte" in v and not (dv is not None and dv >= v["$gte"]):
                return False
            if "$lte" in v and not (dv is not None and dv <= v["$lte"]):
                return False
        elif isinstance(dv, list) and not isinstance(v, list):
            if v not in dv:
                return False
        elif dv != v:
            return False
    return True


class _Cursor:
    def __init__(self, docs):
        self.docs = docs
        self._lim = None

    def sort(self, key, direction=1):
        if isinstance(key, list):
            key, direction = key[0]
        self.docs.sort(key=lambda d: (d.get(key) is None, d.get(key) or ""), reverse=direction == -1)
        return self

    def limit(self, n):
        self._lim = n
        return self

    async def to_list(self, length=1000):
        docs = self.docs[: self._lim] if self._lim is not None else self.docs
        return docs[:length]


class MemoryCollection:
    def __init__(self, owner: "Database", name: str):
        self.owner, self.name = owner, name
        self.docs: list[dict] = []

    def _dirty(self):
        self.owner.dirty = True

    async def insert_one(self, doc: dict):
        d = dict(doc)
        d.setdefault("_id", oid())
        self.docs.append(d)
        self._dirty()

        class R:
            inserted_id = d["_id"]

        return R()

    async def find_one(self, query: dict | None = None):
        for d in self.docs:
            if _match(d, query or {}):
                return dict(d)
        return None

    def find(self, query: dict | None = None):
        return _Cursor([dict(d) for d in self.docs if _match(d, query or {})])

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for d in self.docs:
            if _match(d, query):
                d.update(update.get("$set", {}))
                self._dirty()
                return type("R", (), {"modified_count": 1})()
        if upsert:
            new_doc = {k: v for k, v in query.items() if not isinstance(v, dict)}
            new_doc.update(update.get("$set", {}))
            await self.insert_one(new_doc)
        return type("R", (), {"modified_count": 0})()

    async def count_documents(self, query: dict | None = None):
        return sum(1 for d in self.docs if _match(d, query or {}))

    async def delete_many(self, query: dict | None = None):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _match(d, query or {})]
        self._dirty()
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def delete_one(self, query: dict):
        for i, d in enumerate(self.docs):
            if _match(d, query):
                del self.docs[i]
                self._dirty()
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()


class Database:
    def __init__(self):
        self.mode = "memory"
        self.client = None
        self.db = None
        self.dirty = False
        self.path = Path(os.environ.get("MEMORY_DB_PATH", Path(__file__).parent / "data" / "memory_db.json"))
        self.mem = {name: MemoryCollection(self, name) for name in COLLECTIONS}

    async def connect(self):
        try:
            client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=1500)
            await client.admin.command("ping")
            self.client, self.db, self.mode = client, client[settings.mongo_db], "mongo"
            await self._indexes()
        except Exception:
            self.mode = "memory"
            self._load()

    async def _indexes(self):
        await self.db["users"].create_index("email", unique=True)
        await self.db["profiles"].create_index("user_id")
        await self.db["diet_plans"].create_index([("user_id", 1), ("created_at", -1)])
        await self.db["diary"].create_index([("user_id", 1), ("date", 1)])
        await self.db["weights"].create_index([("user_id", 1), ("date", 1)])

    def col(self, name: str):
        return self.db[name] if self.mode == "mongo" else self.mem[name]

    # -- snapshot persistence for the in-memory fallback ------------------
    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json_util.loads(self.path.read_text(encoding="utf-8"))
            for name, docs in data.items():
                if name in self.mem:
                    self.mem[name].docs = docs
        except Exception:
            pass

    def flush(self):
        if self.mode != "memory" or not self.dirty:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {name: col.docs for name, col in self.mem.items()}
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json_util.dumps(payload), encoding="utf-8")
            tmp.replace(self.path)
            self.dirty = False
        except Exception:
            pass


db = Database()
