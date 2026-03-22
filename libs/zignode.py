from __future__ import annotations

import os, sys, platform, subprocess, inspect, time, datetime, uuid, json, base64, re, ipaddress, copy, asyncio, random, functools, struct, hashlib, importlib.util, logging
from typing import Any
debug = False
try:
  from aiohttp import web
  import aiohttp
  comm_enable = True
except ImportError:
  comm_enable = False
try:
  import netifaces2 as netifaces
  scan_enable = True
except ImportError:
  try:
    import netifaces
    scan_enable = True
  except ImportError:
    scan_enable = False
try:
  import nacl.bindings as nb
  crypto_enable = True
except ImportError:
  crypto_enable = False

start_time = time.time()
__MyName__ = os.path.split(sys.argv[0])[1]
system_type = platform.system()
default_ip = "0.0.0.0"
default_port = 8635
WS_PATH = "/ws"
MANUAL_NODE_LIST = []
MAX_SCAN_FAILS = 16
CALL_TIMEOUT = 15
STALE_SCAN_RETRY_BATCH = 8
DISCOVERY_INTERVAL_SECONDS = 30
ABUT_ACTIVE_GRACE_SECONDS = 75
INACTIVE_TIMEOUT_SECONDS = 95
PORT_SCAN_TIMEOUT_SECONDS = 0.5
PORT_SCAN_CONCURRENCY = 64
STATUS_CHECK_CONCURRENCY = 32
ISLAND_MAINTENANCE_SECONDS = 1.0

_ACTIVE_APP = None

def _active_app():
  if not _ACTIVE_APP:
    raise RuntimeError("zignode app not started")
  return _ACTIVE_APP

DEFAULT_ISLAND_KIND = "generic"
DEFAULT_ISLAND_MODE = "active"
DEFAULT_ISLAND_TOKEN = "admin"
DEFAULT_ISLAND_TOKEN_TTL_MS = 5000

def _now_ms() -> int:
  return int(time.time() * 1000)

def _deepcopy_json(value):
  return copy.deepcopy(value)

def _ensure_dict(value, default=None):
  if isinstance(value, dict):
    return _deepcopy_json(value)
  return {} if default is None else _deepcopy_json(default)

def ensure_runtime(app):
  if "island_state" not in app:
    app["island_state"] = {
      "islands": {},
      "updated_at": _now_ms(),
    }
  state = app["island_state"]
  state.setdefault("islands", {})
  state.setdefault("updated_at", _now_ms())
  return state

def _node_meta(node):
  identity = getattr(node, "identity", {}) or {}
  return {
    "hostname": getattr(node, "hostname", None) or identity.get("hostname"),
    "script_name": getattr(node, "script_name", None) or identity.get("myname"),
    "platform": identity.get("platform"),
    "version": identity.get("version"),
  }

def _normalize_member(member_id, member=None, node=None):
  member = _ensure_dict(member)
  now = _now_ms()
  normalized = {
    "id": str(member_id),
    "mode": str(member.get("mode") or DEFAULT_ISLAND_MODE),
    "joined_at": int(member.get("joined_at") or now),
    "last_seen": int(member.get("last_seen") or now),
    "meta": _ensure_dict(member.get("meta")),
  }
  if member.get("hostname"):
    normalized["hostname"] = member.get("hostname")
  if node and str(member_id) == getattr(node, "id", None):
    meta = _node_meta(node)
    meta.update(normalized["meta"])
    normalized["meta"] = meta
    normalized["hostname"] = meta.get("hostname")
  return normalized

def _normalize_runtime(runtime):
  runtime = _ensure_dict(runtime)
  runtime.setdefault("tokens", {})
  runtime["tokens"] = _ensure_dict(runtime.get("tokens"))
  return runtime

def _normalize_island(snapshot, node=None):
  snapshot = _ensure_dict(snapshot)
  now = _now_ms()
  island_id = str(snapshot.get("id") or uuid.uuid4())
  members_in = snapshot.get("members") or {}
  members = {}
  if isinstance(members_in, dict):
    for member_id, member in members_in.items():
      members[str(member_id)] = _normalize_member(member_id, member, node=node if str(member_id) == getattr(node, "id", None) else None)
  normalized = {
    "id": island_id,
    "name": str(snapshot.get("name") or island_id),
    "kind": str(snapshot.get("kind") or snapshot.get("type") or DEFAULT_ISLAND_KIND),
    "config": _ensure_dict(snapshot.get("config")),
    "runtime": _normalize_runtime(snapshot.get("runtime")),
    "members": members,
    "config_rev": int(snapshot.get("config_rev") or 0),
    "runtime_rev": int(snapshot.get("runtime_rev") or 0),
    "created_at": int(snapshot.get("created_at") or now),
    "updated_at": int(snapshot.get("updated_at") or now),
  }
  meta = _ensure_dict(snapshot.get("meta"))
  if meta:
    normalized["meta"] = meta
  return normalized

def _snapshot_rank(snapshot):
  return (
    int(snapshot.get("config_rev") or 0),
    int(snapshot.get("runtime_rev") or 0),
    int(snapshot.get("updated_at") or 0),
    int(snapshot.get("created_at") or 0),
  )

def _merge_members(existing_members, incoming_members):
  merged = _deepcopy_json(existing_members or {})
  for member_id, incoming in (incoming_members or {}).items():
    current = merged.get(member_id)
    if current is None or int(incoming.get("last_seen") or 0) >= int(current.get("last_seen") or 0):
      merged[member_id] = _deepcopy_json(incoming)
  return merged

def _summarize_island(snapshot, local_id=None):
  snapshot = _normalize_island(snapshot)
  tokens = snapshot.get("runtime", {}).get("tokens", {})
  summary = {
    "id": snapshot["id"],
    "name": snapshot["name"],
    "kind": snapshot["kind"],
    "config_rev": snapshot["config_rev"],
    "runtime_rev": snapshot["runtime_rev"],
    "updated_at": snapshot["updated_at"],
    "member_count": len(snapshot.get("members") or {}),
    "token_names": sorted(tokens.keys()),
  }
  if local_id:
    member = (snapshot.get("members") or {}).get(local_id)
    summary["joined"] = bool(member)
    if member:
      summary["mode"] = member.get("mode")
  return summary

def _store_island_snapshot(app, snapshot):
  state = ensure_runtime(app)
  state["islands"][snapshot["id"]] = _deepcopy_json(snapshot)
  state["updated_at"] = _now_ms()
  return state["islands"][snapshot["id"]]

def local_joined_summaries(app, node):
  state = ensure_runtime(app)
  joined = []
  for snapshot in state["islands"].values():
    if node.id in (snapshot.get("members") or {}):
      joined.append(_summarize_island(snapshot, local_id=node.id))
  return sorted(joined, key=lambda item: (item.get("name") or item["id"]).lower())

def visible_summaries(app, node):
  visible = {}
  for peer_id, peer_data in (getattr(node, "abuts", {}) or {}).items():
    for summary in peer_data.get("islands") or []:
      if not isinstance(summary, dict) or not summary.get("id"):
        continue
      island_id = str(summary["id"])
      item = visible.setdefault(island_id, _deepcopy_json(summary))
      item.setdefault("sources", [])
      if peer_id not in item["sources"]:
        item["sources"].append(peer_id)
      if int(summary.get("updated_at") or 0) >= int(item.get("updated_at") or 0):
        for key, value in summary.items():
          if key != "sources":
            item[key] = _deepcopy_json(value)
  return sorted(visible.values(), key=lambda item: (item.get("name") or item["id"]).lower())

def list_islands(app, node):
  state = ensure_runtime(app)
  known = [_summarize_island(snapshot, local_id=node.id) for snapshot in state["islands"].values()]
  return {
    "joined": sorted([item for item in known if item.get("joined")], key=lambda item: (item.get("name") or item["id"]).lower()),
    "visible": visible_summaries(app, node),
    "nearby": visible_summaries(app, node),
    "known": sorted(known, key=lambda item: (item.get("name") or item["id"]).lower()),
  }

def get_island(app, island_id):
  state = ensure_runtime(app)
  snapshot = state["islands"].get(str(island_id))
  return _deepcopy_json(snapshot) if snapshot else None

def put_island(app, node, snapshot):
  incoming = _normalize_island(snapshot, node=node)
  state = ensure_runtime(app)
  existing = state["islands"].get(incoming["id"])
  if not existing:
    stored = _store_island_snapshot(app, incoming)
    return _deepcopy_json(stored), True

  existing_rank = _snapshot_rank(existing)
  incoming_rank = _snapshot_rank(incoming)
  if incoming_rank > existing_rank:
    merged = incoming
    merged["members"] = _merge_members(existing.get("members"), incoming.get("members"))
  elif incoming_rank == existing_rank:
    merged = _deepcopy_json(existing)
    merged["members"] = _merge_members(existing.get("members"), incoming.get("members"))
    if incoming.get("name") and incoming.get("name") != merged.get("name"):
      merged["name"] = incoming["name"]
    if incoming.get("kind") and incoming.get("kind") != merged.get("kind"):
      merged["kind"] = incoming["kind"]
  else:
    merged = _deepcopy_json(existing)

  changed = merged != existing
  if changed:
    stored = _store_island_snapshot(app, merged)
    return _deepcopy_json(stored), True
  return _deepcopy_json(existing), False

def _mutate_island(app, island_id):
  state = ensure_runtime(app)
  island_id = str(island_id)
  existing = state["islands"].get(island_id)
  if not existing:
    raise KeyError(f"island '{island_id}' not found")
  updated = _deepcopy_json(existing)
  state["islands"][island_id] = updated
  return updated

def join_island(app, node, island=None, island_id=None, name=None, kind=DEFAULT_ISLAND_KIND, config=None, runtime=None, mode=DEFAULT_ISLAND_MODE, meta=None):
  if island:
    snapshot = _normalize_island(island, node=node)
  else:
    snapshot = _normalize_island(
      {
        "id": island_id or str(uuid.uuid4()),
        "name": name or island_id or "island",
        "kind": kind or DEFAULT_ISLAND_KIND,
        "config": config or {},
        "runtime": runtime or {},
      },
      node=node,
    )

  existing = get_island(app, snapshot["id"])
  if existing:
    snapshot = _normalize_island(existing, node=node)
  if name is not None:
    snapshot["name"] = str(name)
  if kind is not None:
    snapshot["kind"] = str(kind)
  if config is not None:
    snapshot["config"] = _ensure_dict(config)
    snapshot["config_rev"] = max(int(snapshot.get("config_rev") or 0), 0) + 1
  elif not snapshot.get("config_rev"):
    snapshot["config_rev"] = 1
  if runtime is not None:
    snapshot["runtime"] = _normalize_runtime(runtime)
    snapshot["runtime_rev"] = max(int(snapshot.get("runtime_rev") or 0), 0) + 1
  elif not snapshot.get("runtime_rev"):
    snapshot["runtime_rev"] = 1

  members = snapshot.setdefault("members", {})
  current = members.get(node.id)
  new_member = _normalize_member(node.id, {"mode": mode, "meta": meta or {}, "joined_at": current.get("joined_at") if current else None}, node=node)
  changed = current != new_member
  members[node.id] = new_member
  if changed:
    snapshot["runtime_rev"] = max(int(snapshot.get("runtime_rev") or 0), 0) + (0 if runtime is not None else 1)
  snapshot["updated_at"] = _now_ms()
  stored = _store_island_snapshot(app, snapshot)
  return _deepcopy_json(stored)

def leave_island(app, node, island_id):
  state = ensure_runtime(app)
  island_id = str(island_id)
  snapshot = get_island(app, island_id)
  if not snapshot:
    return None
  members = snapshot.setdefault("members", {})
  if node.id in members:
    del members[node.id]
    snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
    snapshot["updated_at"] = _now_ms()
  if members:
    stored = _store_island_snapshot(app, snapshot)
    return _deepcopy_json(stored)
  del state["islands"][island_id]
  state["updated_at"] = _now_ms()
  return None

def touch_local_member(app, node, island_id, mode=None, meta=None):
  try:
    snapshot = _mutate_island(app, island_id)
  except KeyError:
    return None
  members = snapshot.setdefault("members", {})
  current = members.get(node.id)
  if current is None:
    current = _normalize_member(node.id, {"mode": mode or DEFAULT_ISLAND_MODE, "meta": meta or {}}, node=node)
    members[node.id] = current
    snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
  else:
    current["last_seen"] = _now_ms()
    if mode is not None and mode != current.get("mode"):
      current["mode"] = mode
      snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
    if meta:
      merged_meta = _ensure_dict(current.get("meta"))
      merged_meta.update(_ensure_dict(meta))
      current["meta"] = merged_meta
      snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
    refreshed = _normalize_member(node.id, current, node=node)
    refreshed["joined_at"] = current.get("joined_at", refreshed["joined_at"])
    refreshed["last_seen"] = _now_ms()
    members[node.id] = refreshed
  snapshot["updated_at"] = _now_ms()
  ensure_runtime(app)["updated_at"] = snapshot["updated_at"]
  return _deepcopy_json(snapshot)

def update_config(app, node, island_id, config, name=None):
  snapshot = _mutate_island(app, island_id)
  new_config = _ensure_dict(config)
  changed = snapshot.get("config") != new_config
  if name is not None and snapshot.get("name") != str(name):
    snapshot["name"] = str(name)
    changed = True
  if changed:
    snapshot["config"] = new_config
    snapshot["config_rev"] = int(snapshot.get("config_rev") or 0) + 1
    snapshot["updated_at"] = _now_ms()
    ensure_runtime(app)["updated_at"] = snapshot["updated_at"]
  return _deepcopy_json(snapshot)

def update_runtime(app, node, island_id, runtime, merge=True):
  snapshot = _mutate_island(app, island_id)
  if merge:
    merged_runtime = _normalize_runtime(snapshot.get("runtime"))
    for key, value in _ensure_dict(runtime).items():
      if key == "tokens":
        tokens = _ensure_dict(merged_runtime.get("tokens"))
        tokens.update(_ensure_dict(value))
        merged_runtime["tokens"] = tokens
      else:
        merged_runtime[key] = _deepcopy_json(value)
    new_runtime = merged_runtime
  else:
    new_runtime = _normalize_runtime(runtime)
  if snapshot.get("runtime") != new_runtime:
    snapshot["runtime"] = new_runtime
    snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
    snapshot["updated_at"] = _now_ms()
    ensure_runtime(app)["updated_at"] = snapshot["updated_at"]
  return _deepcopy_json(snapshot)

def _token_view(token_name, token_state):
  token = _ensure_dict(token_state)
  token["name"] = token_name
  return token

def claim_token(app, node, island_id, token_name=DEFAULT_ISLAND_TOKEN, owner_id=None, ttl_ms=DEFAULT_ISLAND_TOKEN_TTL_MS, force=False, meta=None):
  snapshot = _mutate_island(app, island_id)
  runtime = _normalize_runtime(snapshot.get("runtime"))
  tokens = runtime.setdefault("tokens", {})
  token_name = str(token_name or DEFAULT_ISLAND_TOKEN)
  owner_id = str(owner_id or node.id)
  ttl_ms = int(ttl_ms or DEFAULT_ISLAND_TOKEN_TTL_MS)
  now = _now_ms()
  current = _ensure_dict(tokens.get(token_name))
  current_owner = current.get("owner_id")
  expires_at = int(current.get("expires_at") or 0)
  active = bool(current_owner and expires_at > now)
  if active and current_owner != owner_id and not force:
    return {
      "ok": False,
      "reason": "owned",
      "island_id": str(island_id),
      "token": _token_view(token_name, current),
    }

  changed = (
    current_owner != owner_id
    or int(current.get("ttl_ms") or 0) != ttl_ms
    or _ensure_dict(current.get("meta")) != _ensure_dict(meta)
    or not active
  )
  generation = int(current.get("generation") or 0) + (1 if changed else 0)
  token = {
    "owner_id": owner_id,
    "issued_at": int(current.get("issued_at") or now),
    "updated_at": now,
    "expires_at": now + ttl_ms,
    "ttl_ms": ttl_ms,
    "generation": generation,
    "meta": _ensure_dict(meta),
  }
  tokens[token_name] = token
  runtime["tokens"] = tokens
  snapshot["runtime"] = runtime
  if changed:
    snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
  snapshot["updated_at"] = now
  ensure_runtime(app)["updated_at"] = now
  return {
    "ok": True,
    "changed": changed,
    "island_id": str(island_id),
    "token": _token_view(token_name, token),
  }

def release_token(app, node, island_id, token_name=DEFAULT_ISLAND_TOKEN, owner_id=None, force=False):
  snapshot = _mutate_island(app, island_id)
  runtime = _normalize_runtime(snapshot.get("runtime"))
  tokens = runtime.setdefault("tokens", {})
  token_name = str(token_name or DEFAULT_ISLAND_TOKEN)
  owner_id = str(owner_id or node.id)
  current = _ensure_dict(tokens.get(token_name))
  if not current:
    return {
      "ok": False,
      "reason": "missing",
      "island_id": str(island_id),
      "token_name": token_name,
    }
  if current.get("owner_id") != owner_id and not force:
    return {
      "ok": False,
      "reason": "not_owner",
      "island_id": str(island_id),
      "token": _token_view(token_name, current),
    }
  del tokens[token_name]
  runtime["tokens"] = tokens
  snapshot["runtime"] = runtime
  snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
  snapshot["updated_at"] = _now_ms()
  ensure_runtime(app)["updated_at"] = snapshot["updated_at"]
  return {
    "ok": True,
    "changed": True,
    "island_id": str(island_id),
    "token_name": token_name,
  }

def expire_leases(app):
  state = ensure_runtime(app)
  now = _now_ms()
  changed_any = False
  for island_id, snapshot in list(state["islands"].items()):
    runtime = _normalize_runtime(snapshot.get("runtime"))
    tokens = runtime.setdefault("tokens", {})
    expired = [name for name, token in tokens.items() if int((token or {}).get("expires_at") or 0) <= now]
    if not expired:
      continue
    changed_any = True
    snapshot = _deepcopy_json(snapshot)
    for name in expired:
      tokens.pop(name, None)
    snapshot["runtime"] = runtime
    snapshot["runtime_rev"] = int(snapshot.get("runtime_rev") or 0) + 1
    snapshot["updated_at"] = now
    state["islands"][island_id] = snapshot
  if changed_any:
    state["updated_at"] = now
  return changed_any

_ensure_island_runtime = ensure_runtime
_list_islands = list_islands
_visible_islands = visible_summaries
_local_joined_islands = local_joined_summaries
_get_island = get_island
_put_island = put_island
_join_island = join_island
_leave_island = leave_island
_touch_island_member = touch_local_member
_update_island_config = update_config
_update_island_runtime = update_runtime
_claim_island_token = claim_token
_release_island_token = release_token
_expire_island_leases = expire_leases

def _stream_target_address(target_node_data: dict[str, Any]) -> tuple[str, int]:
  addresses = target_node_data.get("addresses") or []
  if not addresses:
    raise RuntimeError("Target node has no known address.")
  ip, port = addresses[0]
  return str(ip), int(port)

def _stream_target_key(target_node_data: dict[str, Any]) -> str:
  target_id = target_node_data.get("id")
  if target_id:
    return f"id:{target_id}"
  ip, port = _stream_target_address(target_node_data)
  return f"addr:{ip}:{port}"

class _PeerChannel:
  def __init__(
    self,
    session: aiohttp.ClientSession,
    target_node_data: dict[str, Any],
    *,
    ws_path: str = "/ws",
    connect_timeout: float = 15.0,
    request_timeout: float = 15.0,
    logger: logging.Logger | None = None,
  ):
    self._session = session
    self._target_node_data = dict(target_node_data or {})
    self._ws_path = ws_path
    self._connect_timeout = float(connect_timeout)
    self._request_timeout = float(request_timeout)
    self._log = logger or logging.getLogger("zignode.streams")

    self._key = _stream_target_key(self._target_node_data)
    self._ws = None
    self._reader_task = None
    self._connect_lock = asyncio.Lock()
    self._send_lock = asyncio.Lock()
    self._closed = False

    self._pending = {}
    self._stats = {
      "key": self._key,
      "target_id": self._target_node_data.get("id"),
      "connects": 0,
      "reconnects": 0,
      "disconnects": 0,
      "rpc_sent": 0,
      "rpc_recv": 0,
      "events_sent": 0,
      "unknown_frames": 0,
      "errors": 0,
      "last_connect_at": None,
      "last_disconnect_at": None,
      "last_error": None,
    }

  @property
  def key(self) -> str:
    return self._key

  def update_target(self, target_node_data: dict[str, Any]) -> bool:
    target_node_data = dict(target_node_data or {})
    new_key = _stream_target_key(target_node_data)
    reconnect_needed = False
    if self._target_node_data.get("addresses") != target_node_data.get("addresses"):
      reconnect_needed = True
    if self._key != new_key:
      reconnect_needed = True
      self._key = new_key
      self._stats["key"] = new_key
    self._target_node_data = target_node_data
    self._stats["target_id"] = target_node_data.get("id")
    return reconnect_needed

  def is_connected(self) -> bool:
    return bool(self._ws and not self._ws.closed and self._reader_task and not self._reader_task.done())

  def stats(self) -> dict[str, Any]:
    data = dict(self._stats)
    data["connected"] = self.is_connected()
    data["pending"] = len(self._pending)
    ip = port = None
    try:
      ip, port = _stream_target_address(self._target_node_data)
    except Exception:
      pass
    data["address"] = [ip, port] if ip else None
    return data

  async def ensure_connected(self):
    if self._closed:
      raise RuntimeError("Peer channel already closed")
    if self.is_connected():
      return self._ws

    async with self._connect_lock:
      if self.is_connected():
        return self._ws

      if self._ws and not self._ws.closed:
        await self._safe_close_ws()

      ip, port = _stream_target_address(self._target_node_data)
      url = f"ws://{ip}:{port}{self._ws_path}"
      reconnecting = self._stats["connects"] > 0
      try:
        ws = await self._session.ws_connect(url, timeout=self._connect_timeout, protocols=("zignode",))
      except Exception as exc:
        self._record_error(f"connect failed: {exc}")
        raise

      self._ws = ws
      self._reader_task = asyncio.create_task(self._reader_loop(), name=f"zignode-ws-reader:{self._key}")
      self._stats["connects"] += 1
      if reconnecting:
        self._stats["reconnects"] += 1
      self._stats["last_connect_at"] = time.time()
      return ws

  async def request(self, payload: dict[str, Any], timeout: float | None = None):
    request_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    envelope = {
      "type": "rpc",
      "request_id": request_id,
      "payload": payload,
    }
    self._pending[request_id] = future
    try:
      await self._send_with_retry(envelope)
      self._stats["rpc_sent"] += 1
      return await asyncio.wait_for(future, timeout=timeout or self._request_timeout)
    finally:
      self._pending.pop(request_id, None)

  async def emit(
    self,
    call: str,
    *,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    target_id: str = "auto",
    metadata: dict[str, Any] | None = None,
  ) -> str:
    event_id = str(uuid.uuid4())
    envelope = {
      "type": "event",
      "event_id": event_id,
      "payload": {
        "call": call,
        "args": list(args or []),
        "kwargs": dict(kwargs or {}),
        "id": target_id,
      },
    }
    if metadata:
      envelope["metadata"] = dict(metadata)
    await self._send_with_retry(envelope)
    self._stats["events_sent"] += 1
    return event_id

  async def close(self):
    self._closed = True
    await self._safe_close_ws()
    self._fail_pending(RuntimeError("Peer channel closed"))

  async def _send_with_retry(self, envelope: dict[str, Any], retries: int = 1):
    attempts = 0
    while True:
      attempts += 1
      try:
        ws = await self.ensure_connected()
        async with self._send_lock:
          await ws.send_json(envelope, dumps=lambda data: json.dumps(data, default=str))
        return
      except Exception as exc:
        self._record_error(f"send failed: {exc}")
        await self._safe_close_ws()
        if attempts > retries + 1:
          raise

  async def _reader_loop(self):
    ws = self._ws
    try:
      async for msg in ws:
        if msg.type != aiohttp.WSMsgType.TEXT:
          if msg.type == aiohttp.WSMsgType.ERROR:
            self._record_error(f"ws error: {ws.exception()}")
          else:
            self._stats["unknown_frames"] += 1
          continue
        try:
          data = json.loads(msg.data)
        except json.JSONDecodeError:
          self._stats["unknown_frames"] += 1
          continue
        await self._handle_frame(data)
    except asyncio.CancelledError:
      raise
    except Exception as exc:
      self._record_error(f"reader failed: {exc}")
    finally:
      self._stats["disconnects"] += 1
      self._stats["last_disconnect_at"] = time.time()
      self._fail_pending(RuntimeError("WebSocket disconnected"))
      await self._safe_close_ws()

  async def _handle_frame(self, data: Any):
    if not isinstance(data, dict):
      self._stats["unknown_frames"] += 1
      return

    frame_type = data.get("type")
    if frame_type == "rpc_result":
      request_id = str(data.get("request_id") or "")
      future = self._pending.get(request_id)
      if future and not future.done():
        future.set_result(data.get("payload") or [])
        self._stats["rpc_recv"] += 1
      else:
        self._stats["unknown_frames"] += 1
      return

    if frame_type == "event_ack":
      return

    if "result" in data and len(self._pending) == 1:
      _, future = next(iter(self._pending.items()))
      if not future.done():
        future.set_result(data.get("result") or [])
        self._stats["rpc_recv"] += 1
      return

    self._stats["unknown_frames"] += 1

  async def _safe_close_ws(self):
    ws = self._ws
    self._ws = None
    if self._reader_task and self._reader_task is not asyncio.current_task():
      if not self._reader_task.done():
        self._reader_task.cancel()
        try:
          await self._reader_task
        except asyncio.CancelledError:
          pass
        except Exception:
          pass
    self._reader_task = None
    if ws:
      try:
        await ws.close()
      except Exception:
        pass

  def _fail_pending(self, exc: Exception):
    pending = list(self._pending.items())
    self._pending.clear()
    for _, future in pending:
      if not future.done():
        future.set_exception(exc)

  def _record_error(self, message: str):
    self._stats["errors"] += 1
    self._stats["last_error"] = str(message)
    self._log.debug("zignode stream peer %s: %s", self._key, message)

class ZignodeStreamPool:
  def __init__(
    self,
    session,
    *,
    ws_path: str = "/ws",
    connect_timeout: float = 15.0,
    request_timeout: float = 15.0,
    logger: logging.Logger | None = None,
  ):
    self._session = session
    self._ws_path = ws_path
    self._connect_timeout = float(connect_timeout)
    self._request_timeout = float(request_timeout)
    self._log = logger or logging.getLogger("zignode.streams")
    self._channels = {}
    self._lock = asyncio.Lock()

  async def request(self, target_node_data: dict[str, Any], payload: dict[str, Any], timeout: float | None = None):
    channel = await self._get_channel(target_node_data)
    try:
      return await channel.request(payload, timeout=timeout)
    except Exception:
      await self.close_target(target_node_data)
      raise

  async def emit(
    self,
    target_node_data: dict[str, Any],
    call: str,
    *,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    target_id: str = "auto",
    metadata: dict[str, Any] | None = None,
  ) -> str:
    channel = await self._get_channel(target_node_data)
    try:
      return await channel.emit(call, args=args, kwargs=kwargs, target_id=target_id, metadata=metadata)
    except Exception:
      await self.close_target(target_node_data)
      raise

  async def close_target(self, target_node_data_or_key: dict[str, Any] | str):
    key = target_node_data_or_key if isinstance(target_node_data_or_key, str) else _stream_target_key(target_node_data_or_key)
    async with self._lock:
      channel = self._channels.pop(key, None)
    if channel:
      await channel.close()

  async def close(self):
    async with self._lock:
      channels = list(self._channels.values())
      self._channels = {}
    for channel in channels:
      await channel.close()

  async def _get_channel(self, target_node_data: dict[str, Any]) -> _PeerChannel:
    key = _stream_target_key(target_node_data)
    async with self._lock:
      channel = self._channels.get(key)
      if channel is None:
        channel = _PeerChannel(
          self._session,
          target_node_data,
          ws_path=self._ws_path,
          connect_timeout=self._connect_timeout,
          request_timeout=self._request_timeout,
          logger=self._log,
        )
        self._channels[key] = channel
        return channel

      reconnect_needed = channel.update_target(target_node_data)
      if reconnect_needed and channel.is_connected():
        await channel.close()
        replacement = _PeerChannel(
          self._session,
          target_node_data,
          ws_path=self._ws_path,
          connect_timeout=self._connect_timeout,
          request_timeout=self._request_timeout,
          logger=self._log,
        )
        self._channels[key] = replacement
        return replacement
      return channel

  def stats(self) -> dict[str, Any]:
    return {
      "peers": {key: channel.stats() for key, channel in sorted(self._channels.items())},
      "peer_count": len(self._channels),
    }

cc = {
  "RESET": "\033[0m", "NOCOLOR": "\033[39m", "BLACK": "\033[30m", "DRED": "\033[31m", "DGREEN": "\033[32m",
  "ORANGE": "\033[33m", "BLUE": "\033[34m", "VIOLET": "\033[35m", "CYAN": "\033[36m", "LGRAY": "\033[37m",
  "DGRAY": "\033[90m", "RED": "\033[91m", "GREEN": "\033[92m", "YELLOW": "\033[93m", "DBLUE": "\033[94m",
  "PINK": "\033[95m", "LBLUE": "\033[96m", "WHITE": "\033[97m"
}
favicon_data = base64.b64decode("AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQAMAAAAAAAAAAIAAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO2AAIBZAAAAAAAAAACAAIBkgACA/4AAgPqAAIDYgACA2IAAgNiAAIDYgACA2IAAgNiAAIDYgACA/4AAgP+AAICjgACABwAAAAAAAAAAAAAAAIAAgOmAAID/gACAPIAAgAJAAEACQABAAkAAQAKAAIACgACAJoAAgNCAAIDwgACATgAAAAAAAAAAAAAAAAAAAACAAIAygACA/4AAgO4AAAAAAAAAAAAAAAAAAAAAAAAAAIAAgIWAAID/gACAjgAAAAAAAAAAAAAAAIAAgEGAAIDogACA24AAgDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAIASgACA/4AAgPuAAIAGAAAAAIAAgAOAAICYgACA/4AAgHsAAAAAAAAAAEAAQBIAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgJaAAID/gACAoQAAAACAAIBdgACA+IAAgL+AAIAYAAAAAAAAAACAAICDgACA6IAAgAwAAAAAAAAAAAAAAACAAIAEgACA+YAAgP+AAIAmgACAsoAAgPyAAIBnAAAAAAAAAACAAIA6gACA5IAAgN6AAIA0AAAAAAAAAAAAAAAAAAAAAIAAgGGAAID/gaca9IAAgP2AAICjgACABwAAAAAAAAAAgACAkoAAgP+AAIB+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACA6YAAgP+AAIDxgACAT4AAgAKAAIACgACAUYAAgPOAAIDJgACAHgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgDKAAID/gACA/4AAgNmAAIDYgACA2IAAgN2AAID/gACAbwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACAvoAAgO+AAIDvgACA74AAgO+AAIDvgACAw4AAgA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAJAAEAPQABAD0AAQA9AAEAPQABAD0AAQA8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAP//AAAABwAAgAcAAJ/PAADPjwAAz58AAOc/AADjOQAA8nkAAPhzAAD48wAA/AcAAPwHAAD//wAA//8AAA==")

def split_long_string(input_string, max_length=90):
  words = []
  wordst = input_string.split()
  for word in wordst:
    if len(re.sub(r"\033\[\d+m", "", str(word))) >= max_length:
      maxl = max_length - 2
      wordcut = [word[i : i + maxl] for i in range(0, len(word), maxl)]
      words += wordcut
    else:
      words.append(word)
  result_strings = []
  current_string = ""
  for word in words:
    if (len(re.sub(r"\033\[\d+m", "", str(current_string))) + len(re.sub(r"\033\[\d+m", "", str(word)))) <= max_length:
      current_string += word + " "
    else:
      result_strings.append(current_string.strip())
      current_string = word + " "
  if current_string:
    result_strings.append(current_string.strip())
  return result_strings

def frame(lines="", COLOR="NOCOLOR", frames=25, framemax=92, display=True):
  lineslst = isinstance(lines, list)
  linelist = []
  lll = frames - 2
  if lineslst:
    for sline in lines:
      sline = str(sline)
      ll = len(re.sub(r"\033\[\d+m", "", str(sline)))
      if ll + 2 > framemax:
        sublines = split_long_string(sline, framemax - 2)
        for ssline in sublines:
          ll = len(re.sub(r"\033\[\d+m", "", str(ssline)))
          lll = max(ll, lll)
          linelist.append(ssline)
      else:
        lll = max(ll, lll)
        linelist.append(sline)
  else:
    lines = str(lines)
    ll = len(re.sub(r"\033\[\d+m", "", str(lines)))
    if ll + 2 > framemax:
      sublines = split_long_string(lines, framemax - 2)
      for ssline in sublines:
        ll = len(re.sub(r"\033\[\d+m", "", str(ssline)))
        lll = max(ll, lll)
        linelist.append(ssline)
    else:
      lll = max(ll, lll)
      linelist.append(lines)
  frame_width = lll + 2
  output_lines = []
  output_lines.append(cc[COLOR] + "┌" + "─" * frame_width + "┐" + cc[COLOR])
  for sline in linelist:
    padding = " " * (frame_width - len(re.sub(r"\033\[\d+m", "", str(sline))) - 2)
    output_lines.append(f"{cc[COLOR]}│ {cc['NOCOLOR']}{sline}{padding}{cc[COLOR]} │")
  output_lines.append(cc[COLOR] + "└" + "─" * frame_width + "┘" + cc["RESET"])
  output_string = "\n".join(output_lines)
  if display:
    print(output_string)
  return output_string

def get_computer_name():
  try:
    if platform.system() == "Darwin":
      try:
        return subprocess.check_output(["scutil", "--get", "ComputerName"], text=True).strip()
      except (subprocess.CalledProcessError, FileNotFoundError):
        return subprocess.check_output(["hostname"], text=True).strip()
    else:
      return subprocess.check_output(["hostname"], text=True).strip()
  except (subprocess.CalledProcessError, FileNotFoundError):
    return platform.node()

if crypto_enable:
  _NP = b"Noise_XX_25519_ChaChaPoly_BLAKE2b"

  def _b2b(d): return hashlib.blake2b(d, digest_size=64).digest()
  def _b2b_k(k, d): return hashlib.blake2b(d, key=k[:64], digest_size=64).digest()
  def _hkdf2(ck, ikm):
    t = _b2b_k(ck, ikm)
    o1 = _b2b_k(t, b'\x01')
    return o1, _b2b_k(t, o1 + b'\x02')
  def _aead_enc(k, n, ad, pt):
    return nb.crypto_aead_chacha20poly1305_ietf_encrypt(pt, ad, b'\x00'*4 + struct.pack('<Q', n), k)
  def _aead_dec(k, n, ad, ct):
    return nb.crypto_aead_chacha20poly1305_ietf_decrypt(ct, ad, b'\x00'*4 + struct.pack('<Q', n), k)

  class _NoiseXX:
    def __init__(self, ini, s_priv, s_pub):
      self.ini = ini
      self.s = (s_priv, s_pub)
      e_priv = nb.randombytes(32)
      self.e = (e_priv, nb.crypto_scalarmult_base(e_priv))
      self.re = self.rs = None
      p = _NP
      self.h = (p + b'\x00' * (64 - len(p))) if len(p) <= 64 else _b2b(p)
      self.ck = bytes(self.h)
      self.k = None; self.n = 0; self._ph = 0
      self.done = False; self.c_s = self.c_r = None; self.n_s = self.n_r = 0

    def _mk(self, dh):
      self.ck, tmp = _hkdf2(self.ck, dh)
      self.k = tmp[:32]; self.n = 0

    def _mh(self, d): self.h = _b2b(self.h + d)

    def _eah(self, pt):
      if self.k is None: self._mh(pt); return pt
      ct = _aead_enc(self.k, self.n, self.h, pt); self._mh(ct); self.n += 1; return ct

    def _dah(self, ct):
      if self.k is None: self._mh(ct); return ct
      pt = _aead_dec(self.k, self.n, self.h, ct); self._mh(ct); self.n += 1; return pt

    def _split(self):
      k1, k2 = _hkdf2(self.ck, b'')
      self.c_s, self.c_r = (k1[:32], k2[:32]) if self.ini else (k2[:32], k1[:32])
      self.n_s = self.n_r = 0; self.done = True

    def write_msg(self, payload=b''):
      ph = self._ph
      if self.ini and ph == 0:
        self._mh(self.e[1])
        buf = self.e[1] + self._eah(payload)
      elif not self.ini and ph == 1:
        self._mh(self.e[1]); self._mk(nb.crypto_scalarmult(self.e[0], self.re))
        enc_s = self._eah(self.s[1]); self._mk(nb.crypto_scalarmult(self.s[0], self.re))
        buf = self.e[1] + enc_s + self._eah(payload)
      elif self.ini and ph == 2:
        enc_s = self._eah(self.s[1]); self._mk(nb.crypto_scalarmult(self.s[0], self.re))
        buf = enc_s + self._eah(payload); self._split()
      else:
        raise RuntimeError(f"write_msg: unexpected phase={ph} ini={self.ini}")
      self._ph += 1; return buf

    def read_msg(self, msg):
      ph = self._ph
      if not self.ini and ph == 0:
        self.re = msg[:32]; self._mh(self.re)
        payload = self._dah(msg[32:])
      elif self.ini and ph == 1:
        self.re = msg[:32]; self._mh(self.re); self._mk(nb.crypto_scalarmult(self.e[0], self.re))
        self.rs = self._dah(msg[32:80]); self._mk(nb.crypto_scalarmult(self.e[0], self.rs))
        payload = self._dah(msg[80:])
      elif not self.ini and ph == 2:
        self.rs = self._dah(msg[:48]); self._mk(nb.crypto_scalarmult(self.e[0], self.rs))
        payload = self._dah(msg[48:]); self._split()
      else:
        raise RuntimeError(f"read_msg: unexpected phase={ph} ini={self.ini}")
      self._ph += 1; return payload

    def enc(self, pt):
      ct = _aead_enc(self.c_s, self.n_s, b'', pt); self.n_s += 1; return ct

    def dec(self, ct):
      pt = _aead_dec(self.c_r, self.n_r, b'', ct); self.n_r += 1; return pt

def _check_trust(node, pub_bytes):
  key_hex = pub_bytes.hex()
  if key_hex in node.revoked_keys: return False
  if key_hex not in node.trusted_keys:
    node.trusted_keys.add(key_hex)
    debug and frame(f"New peer key: {key_hex[:16]}...", "CYAN")
  return True

def _sd_notify(msg):
  sock = os.environ.get('NOTIFY_SOCKET')
  if not sock: return
  import socket
  with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
    s.connect(sock); s.send(msg.encode() if isinstance(msg, str) else msg)

def _streams_logger():
  return logging.getLogger("zignode.streams")

def _supports_streams(target_node_data):
  return bool(target_node_data and target_node_data.get("streams_enabled") and target_node_data.get("ws_enabled"))

async def _emit_via_app(app, call, args=None, kwargs=None, target_ids=None, include_self=False, metadata=None):
  node = app['node']
  args = args or []
  kwargs = kwargs or {}
  results = []
  async with node.lock:
    abuts_copy = {nid: data for nid, data in node.abuts.items() if data.get("active")}

  direct_candidates = {}
  proxy_candidates = []
  if target_ids:
    target_ids_set = {target_ids} if isinstance(target_ids, str) else set(target_ids)
    for target_id in target_ids_set:
      if target_id == node.id:
        continue
      if target_id in abuts_copy:
        direct_candidates[target_id] = abuts_copy[target_id]
        continue
      for abut_id, abut_data in abuts_copy.items():
        if target_id in abut_data.get("abut_nodes", {}):
          proxy_candidates.append((abut_id, target_id, abut_data))
          break
    if not direct_candidates and not proxy_candidates and not include_self:
      return [_format_response("auto", None, status="Failed", error=f"No targets found for '{call}'.")]
  else:
    direct_candidates = {
      nid: data for nid, data in abuts_copy.items()
      if call in data.get("capabilities", [])
    }
    if not direct_candidates and not include_self:
      return [_format_response("auto", None, status="Failed", error=f"No targets found for '{call}'.")]

  if include_self and call in node.local_functions:
    try:
      value = await run_local_function(node.local_functions, call, args, kwargs)
      results.append(_format_response(node.id, value))
    except Exception as e:
      results.append(_format_response(node.id, None, status="Failed", error=str(e)))

  stream_pool = app.get('stream_pool')
  session = app.get('client_session')

  for target_id, target_data in direct_candidates.items():
    try:
      if stream_pool and _supports_streams(target_data):
        event_id = await stream_pool.emit(
          target_data,
          call,
          args=args,
          kwargs=kwargs,
          target_id=target_id,
          metadata=metadata,
        )
        results.append(_format_response(target_id, {"ok": True, "event_id": event_id, "transport": "pooled_ws"}))
      else:
        payload = {"call": call, "args": args, "kwargs": kwargs, "id": target_id}
        rpc_result = await _send_request(app, session, target_data, payload, node)
        results.append(rpc_result[0] if rpc_result else _format_response(target_id, None, status="Failed", error="No response from target."))
    except Exception as e:
      results.append(_format_response(target_id, None, status="Failed", error=f"emit failed: {e}"))

  for proxy_id, final_target_id, proxy_data in proxy_candidates:
    try:
      payload = {
        "call": "emit",
        "kwargs": {
          "call": call,
          "args": args,
          "kwargs": kwargs,
          "target_ids": [final_target_id],
          "metadata": metadata or {},
        },
        "id": proxy_id,
      }
      rpc_result = await _send_request(app, session, proxy_data, payload, node)
      result = rpc_result[0] if rpc_result else _format_response(final_target_id, None, status="Failed", error="No response from proxy.")
      result["routed_by"] = proxy_id
      results.append(result)
    except Exception as e:
      results.append(_format_response(final_target_id, None, status="Failed", error=f"proxy emit failed: {e}", routed_by=proxy_id))

  return results

async def emit(call, args=None, kwargs=None, target_ids=None, include_self=False, metadata=None):
  return await _emit_via_app(_active_app(), call, args=args, kwargs=kwargs, target_ids=target_ids, include_self=include_self, metadata=metadata)

def stream_stats():
  app = _active_app()
  pool = app.get('stream_pool')
  return pool.stats() if pool else {"peers": {}, "peer_count": 0}

def islands():
  app = _active_app()
  return _list_islands(app, app['node'])

def island_state(island_id):
  return _get_island(_active_app(), island_id)

def _checksum(path):
  return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]

def _load_config(path=None):
  script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
  for p in filter(None, [path, os.path.join(script_dir, 'zignode.config'), 'zignode.config']):
    if os.path.exists(p):
      with open(p) as f: return json.load(f), os.path.abspath(p)
  return {}, None

def _resolve_plugin(name_or_path):
  if os.path.isabs(name_or_path):
    return name_or_path if os.path.exists(name_or_path) else None
  for base in [os.path.dirname(os.path.abspath(sys.argv[0])), os.getcwd()]:
    p = os.path.join(base, name_or_path if name_or_path.endswith('.py') else name_or_path + '.py')
    if os.path.exists(p): return p
  return None

def _import_plugin(path):
  spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return {n: o for n, o in vars(mod).items() if inspect.isfunction(o) and not n.startswith('_')}

def _apply_plugins(node, plugin_list):
  new_paths = {}
  for name in plugin_list:
    p = _resolve_plugin(name)
    if p: new_paths[p] = name
    else: frame(f"Plugin not found: {name}", "RED")

  for path in list(node.plugin_registry.keys()):
    if path not in new_paths:
      for fn in node.plugin_registry[path]['funcs']:
        if fn not in node.core_functions: node.local_functions.pop(fn, None)
      del node.plugin_registry[path]
      debug and frame(f"Plugin unloaded: {os.path.basename(path)}", "ORANGE")

  for path, name in new_paths.items():
    try:
      cur = _checksum(path)
      if path in node.plugin_registry and node.plugin_registry[path]['sum'] == cur: continue
      for fn in node.plugin_registry.get(path, {}).get('funcs', []):
        if fn not in node.core_functions: node.local_functions.pop(fn, None)
      funcs = _import_plugin(path)
      node.local_functions.update(funcs)
      node.plugin_registry[path] = {'sum': cur, 'funcs': list(funcs.keys())}
      frame(f"Plugin {'reloaded' if path in node.plugin_registry else 'loaded'}: {os.path.basename(path)} {list(funcs.keys())}", "DGREEN")
    except Exception as e:
      frame(f"Plugin error {os.path.basename(path)}: {e}", "RED")

  node.identity['capabilities'] = list(node.local_functions.keys())

async def config_watcher(app):
  path = app.get('config_path')
  if not path: return
  while True:
    await asyncio.sleep(5)
    try:
      cur = _checksum(path)
      if cur != app['config_sum']:
        app['config_sum'] = cur
        cfg = json.load(open(path))
        app['config'] = cfg
        _apply_plugins(app['node'], cfg.get('plugins', []))
        debug and frame(f"Config reloaded: {path}", "DGREEN")
    except asyncio.CancelledError: break
    except Exception as e: debug and frame(f"Config watch error: {e}", "RED")

async def island_maintenance_loop(app):
  while True:
    try:
      _expire_island_leases(app)
      for island in _local_joined_islands(app, app['node']):
        _touch_island_member(app, app['node'], island["id"])
    except asyncio.CancelledError:
      break
    except Exception as e:
      debug and frame(f"Island maintenance error: {e}", "RED")
    await asyncio.sleep(ISLAND_MAINTENANCE_SECONDS)

async def run_local_function(scope, func_name, params, kwargs):
  params = [params] if not isinstance(params, list) else params
  kwargs = kwargs or {}
  try:
    target_func = scope.get(func_name)
    if not target_func: raise ValueError(f"Function '{func_name}' not found")
    if asyncio.iscoroutinefunction(target_func):
      return await target_func(*params, **kwargs)
    else:
      loop = asyncio.get_running_loop()
      return await loop.run_in_executor(None, functools.partial(target_func, *params, **kwargs))
  except Exception as e:
    return {"error": f"Execution of '{func_name}' failed: {e}"}

def _format_response(id, value, status="Success", routed_by=None, error=None):
  response = {"id": id, "status": status, "value": value}
  if routed_by: response["routed_by"] = routed_by
  if error: response["value"] = None; response["error"] = str(error)
  return response

async def _send_request_ws(session, target_node_data, payload):
  if not target_node_data.get("addresses"):
    raise RuntimeError("Target node has no known address.")
  target_ip, target_port = target_node_data["addresses"][0]
  url = f"ws://{target_ip}:{target_port}{WS_PATH}"
  target_id = payload.get('id', 'unknown')
  try:
    async with session.ws_connect(url, timeout=CALL_TIMEOUT) as ws:
      await ws.send_json(payload)
      msg = await asyncio.wait_for(ws.receive(), timeout=CALL_TIMEOUT)
      if msg.type == aiohttp.WSMsgType.TEXT:
        rj = json.loads(msg.data)
        return rj["result"] if "result" in rj and isinstance(rj.get("result"), list) else [_format_response(target_id, rj)]
      raise RuntimeError(f"Unexpected WS message type: {msg.type}")
  except Exception as e:
    raise RuntimeError(f"WebSocket request failed: {e}") from e

async def _send_request_http(session, target_node_data, payload):
  if not target_node_data.get("addresses"):
    return [_format_response(payload.get('id', 'unknown'), None, status="Failed", error="No address.")]
  target_ip, target_port = target_node_data["addresses"][0]
  url = f"http://{target_ip}:{target_port}/"
  target_id = payload.get('id', 'unknown')
  try:
    async with session.post(url, json=payload, timeout=CALL_TIMEOUT) as response:
      response.raise_for_status()
      try:
        rj = await response.json()
        return rj["result"] if "result" in rj and isinstance(rj.get("result"), list) else [_format_response(target_id, rj)]
      except (aiohttp.ContentTypeError, json.JSONDecodeError):
        return [_format_response(target_id, await response.text(), status="Success")]
  except aiohttp.ClientResponseError as e:
    return [_format_response(target_id, None, status="Failed", error=f"HTTP Error: {e.status} {e.message}")]
  except asyncio.TimeoutError:
    return [_format_response(target_id, None, status="Failed", error="Request timed out.")]
  except Exception as e:
    return [_format_response(target_id, None, status="Failed", error=f"Request failed: {e}")]

async def _send_request_secure_ws(node, target_node_data, payload):
  if not target_node_data.get("addresses"):
    raise RuntimeError("Target node has no known address.")
  target_ip, target_port = target_node_data["addresses"][0]
  url = f"ws://{target_ip}:{target_port}{WS_PATH}"
  target_id = payload.get('id', 'unknown')
  connector = aiohttp.TCPConnector()
  try:
    async with aiohttp.ClientSession(connector=connector) as session:
      async with session.ws_connect(url, protocols=['zignode-secure'], timeout=CALL_TIMEOUT) as ws:
        noise = _NoiseXX(True, node.s_priv, node.s_pub)
        await ws.send_bytes(noise.write_msg())
        m2 = await asyncio.wait_for(ws.receive(), timeout=CALL_TIMEOUT)
        noise.read_msg(m2.data)
        await ws.send_bytes(noise.write_msg())
        if not _check_trust(node, noise.rs):
          raise RuntimeError(f"Revoked key: {noise.rs.hex()[:16]}...")
        await ws.send_bytes(noise.enc(json.dumps(payload).encode()))
        raw = await asyncio.wait_for(ws.receive(), timeout=CALL_TIMEOUT)
        if raw.type == aiohttp.WSMsgType.BINARY:
          rj = json.loads(noise.dec(raw.data))
          return rj["result"] if "result" in rj and isinstance(rj.get("result"), list) else [_format_response(target_id, rj)]
        raise RuntimeError(f"Unexpected secure WS message type: {raw.type}")
  except Exception as e:
    raise RuntimeError(f"Secure WS request failed: {e}") from e
  finally:
    await connector.close()

async def _send_request(app, session, target_node_data, payload, node=None):
  stream_pool = app.get('stream_pool') if app else None
  if stream_pool and _supports_streams(target_node_data):
    try:
      return await stream_pool.request(target_node_data, payload)
    except Exception as e:
      debug and frame(f"Pooled WS failed, falling back: {e}", "ORANGE")
  if node and crypto_enable and target_node_data.get("encrypted_ws_enabled") and node.s_priv:
    try:
      return await _send_request_secure_ws(node, target_node_data, payload)
    except Exception as e:
      debug and frame(f"Secure WS failed, falling back: {e}", "ORANGE")
  if target_node_data.get("ws_enabled"):
    try:
      return await _send_request_ws(session, target_node_data, payload)
    except Exception:
      pass
  return await _send_request_http(session, target_node_data, payload)

async def _broadcast(node, session, func_name, args=None, kwargs=None, target_ids=None, include_self=False):
  args = args or []; kwargs = kwargs or {}
  app = _active_app()
  async with node.lock:
    abuts_copy = {nid: data for nid, data in node.abuts.items() if data.get("active")}
  if target_ids:
    target_ids_set = {target_ids} if isinstance(target_ids, str) else set(target_ids)
    candidates = {nid: data for nid, data in abuts_copy.items() if nid in target_ids_set}
  else:
    candidates = {nid: data for nid, data in abuts_copy.items() if func_name in data.get("capabilities", [])}
  tasks = [_send_request(app, session, ndata, {"call": func_name, "args": args, "kwargs": kwargs, "id": nid}, node) for nid, ndata in candidates.items()]
  results = []
  if include_self and func_name in node.local_functions:
    results.append(_format_response(node.id, await run_local_function(node.local_functions, func_name, args, kwargs)))
  if tasks:
    task_results = await asyncio.gather(*tasks, return_exceptions=True)
    for tres in task_results:
      if isinstance(tres, Exception): results.append(_format_response("unknown", None, status="Failed", error=str(tres)))
      else: results.extend(tres)
  if not results and not candidates and not include_self:
    results.append(_format_response("auto", None, status="Failed", error=f"No targets found for '{func_name}'."))
  return results

async def _process_single_call(app, payload):
  node = app['node']; session = app['client_session']
  func_name = payload.get("call")
  if not func_name:
    return _format_response(node.id, None, status="Failed", error="Missing 'call' parameter.")
  args = payload.get("args", []); kwargs = payload.get("kwargs", {}); target_id = payload.get("id", "auto")
  if target_id != "auto":
    if target_id == node.id:
      return _format_response(node.id, await run_local_function(node.local_functions, func_name, args, kwargs))
    async with node.lock:
      abuts_copy = dict(node.abuts)
    if target_id in abuts_copy and abuts_copy[target_id].get("active"):
      result_list = await _send_request(app, session, abuts_copy[target_id], payload, node)
      return result_list[0] if result_list else _format_response(target_id, None, status="Failed", error="No response from direct abut.")
    for abut_id, abut_data in abuts_copy.items():
      if not abut_data.get("active"): continue
      if target_id in abut_data.get("abut_nodes", {}):
        result_list = await _send_request(app, session, abut_data, payload, node)
        if not result_list: return _format_response(target_id, None, status="Failed", error="No response from proxy node.")
        result_list[0]["routed_by"] = abut_id; return result_list[0]
    return _format_response(target_id, None, status="Failed", error="Target node not found or inactive.")
  if func_name in node.local_functions:
    return _format_response(node.id, await run_local_function(node.local_functions, func_name, args, kwargs))
  async with node.lock:
    abuts_copy = dict(node.abuts)
  direct_candidates = [nid for nid, ndata in abuts_copy.items() if ndata.get("active") and func_name in ndata.get("capabilities", [])]
  if direct_candidates:
    chosen_id = random.choice(direct_candidates)
    payload["id"] = chosen_id
    result_list = await _send_request(app, session, abuts_copy[chosen_id], payload, node)
    return result_list[0] if result_list else _format_response(chosen_id, None, status="Failed", error="No response from chosen abut.")
  routed_candidates = []
  for abut_id, abut_data in abuts_copy.items():
    if not abut_data.get("active"): continue
    for n_of_n_id, n_of_n_data in abut_data.get("abut_nodes", {}).items():
      if n_of_n_id != node.id and n_of_n_id not in abuts_copy:
        if func_name in n_of_n_data.get("capabilities", []):
          routed_candidates.append({"proxy_id": abut_id, "target_id": n_of_n_id})
  if routed_candidates:
    chosen_route = random.choice(routed_candidates)
    proxy_id = chosen_route["proxy_id"]; final_target_id = chosen_route["target_id"]
    payload["id"] = final_target_id
    result_list = await _send_request(app, session, abuts_copy[proxy_id], payload, node)
    if not result_list: return _format_response(final_target_id, None, status="Failed", error="No response from proxy for routed call.")
    result_list[0]["routed_by"] = proxy_id; return result_list[0]
  return _format_response("auto", None, status="Failed", error=f"No node found with capability '{func_name}'.")

class Node:
  def __init__(self, local_functions, scan_mode='full', name=None, s_priv=None, s_pub=None):
    self.id = str(uuid.uuid4())
    self.start_time = time.time()
    self.script_name = name if name else os.path.basename(sys.argv[0])
    self.hostname = get_computer_name()
    self.abuts = {}; self.scan_targets = {}; self.lock = asyncio.Lock()
    self.local_functions = local_functions; self.scan_mode = scan_mode
    self.s_priv = s_priv; self.s_pub = s_pub
    self.trusted_keys = set(); self.revoked_keys = set()
    self.core_functions = set(local_functions.keys())
    self.plugin_registry = {}
    self.identity = {
      "id": self.id, "myname": self.script_name, "version": "25.4",
      "type": "complex" if comm_enable and scan_enable else "simple",
      "started": self.start_time, "hostname": self.hostname,
      "platform": platform.system(), "capabilities": list(self.local_functions.keys()),
      "addresses": [], "ws_enabled": comm_enable,
      "encrypted_ws_enabled": bool(crypto_enable and s_pub),
      "public_key": s_pub.hex() if s_pub else None,
      "streams_enabled": True,
      "islands_enabled": True,
      "ws_mux_enabled": True,
    }

def get_all_lan_ips():
  if not scan_enable: return []
  ips = set()
  virtual_interface_prefixes = ('docker', 'br-', 'veth', 'virbr', 'vmnet', 'vbox', 'wsl', 'zt', 'tailscale')
  try:
    for interface in netifaces.interfaces():
      is_virtual = interface.startswith(virtual_interface_prefixes)
      if_addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET)
      if not if_addresses: continue
      for addr_info in if_addresses:
        ip = addr_info.get("addr"); netmask = addr_info.get("netmask") or addr_info.get("mask")
        if not (ip and netmask) or ip.startswith("127."): continue
        try:
          network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
          if is_virtual and network.prefixlen < 23: continue
          if network.prefixlen >= 16 and network.num_addresses < 65536:
            ips.update(str(host) for host in network.hosts())
        except ValueError:
          continue
  except Exception:
    pass
  return list(ips)

async def scan_port_wrapper(sem, ip, port, timeout=PORT_SCAN_TIMEOUT_SECONDS):
  async with sem:
    try:
      _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
      writer.close(); await writer.wait_closed(); return (ip, port)
    except (asyncio.TimeoutError, OSError):
      return None

async def check_node_status_wrapper(sem, session, ip, port, timeout=5.0):
  async with sem:
    url = f"http://{ip}:{port}/status"
    try:
      async with session.get(url, timeout=timeout) as response:
        if response.status == 200:
          data = await response.json()
          node_id = data.get("id")
          if node_id: return node_id, data, (ip, port)
    except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
      pass
  return None, None, None

async def discover_and_update_nodes(app, full_scan=False):
  node = app['node']; session = app['client_session']
  port_scan_sem = asyncio.Semaphore(PORT_SCAN_CONCURRENCY)
  status_check_sem = asyncio.Semaphore(STATUS_CHECK_CONCURRENCY)
  async with node.lock:
    scan_targets_to_check = {addr for addr, data in node.scan_targets.items() if data.get("fails", 0) < MAX_SCAN_FAILS}
    stale_scan_targets = [
      addr for addr, data in sorted(node.scan_targets.items())
      if data.get("fails", 0) >= MAX_SCAN_FAILS
    ]
    if stale_scan_targets:
      scan_targets_to_check.update(stale_scan_targets[:STALE_SCAN_RETRY_BATCH])
    known_targets = set(scan_targets_to_check)
    if full_scan:
      known_targets.update(node.scan_targets.keys())
    port_scan_candidates = set()
    if full_scan and scan_enable:
      lan_ips = await asyncio.to_thread(get_all_lan_ips)
      port_scan_candidates = {(ip, default_port) for ip in lan_ips}
  known_targets.update(MANUAL_NODE_LIST)
  known_targets.add(("127.0.0.1", default_port))
  port_scan_candidates.difference_update(known_targets)
  targets_this_cycle = set(known_targets)
  status_targets = set(known_targets)
  if port_scan_candidates:
    port_scan_tasks = [scan_port_wrapper(port_scan_sem, ip, port) for ip, port in port_scan_candidates]
    status_targets.update({res for res in await asyncio.gather(*port_scan_tasks) if res})
  check_timeout = 5.0 if full_scan else 12.0
  status_results = await asyncio.gather(*[check_node_status_wrapper(status_check_sem, session, ip, port, timeout=check_timeout) for ip, port in status_targets])
  found_nodes_buffer = {}; responsive_addresses = set()
  for node_id, data, address in status_results:
    if not node_id: continue
    responsive_addresses.add(address)
    if node_id == node.id:
      if address[0] != '127.0.0.1' and list(address) not in node.identity["addresses"]:
        node.identity["addresses"].append(list(address))
      continue
    if node_id not in found_nodes_buffer:
      found_nodes_buffer[node_id] = {"data": data, "found_at": set()}
    if address[0] != '127.0.0.1':
      found_nodes_buffer[node_id]["found_at"].add(address)
  async with node.lock:
    now = time.time()
    old_addr_map = {tuple(addr): nid for nid, data in node.abuts.items() for addr in data.get('addresses', [])}
    ids_to_remove = set()
    for nid, discovered_info in found_nodes_buffer.items():
      for addr in discovered_info.get('found_at', set()):
        if addr in old_addr_map and old_addr_map[addr] != nid:
          ids_to_remove.add(old_addr_map[addr])
    for nid in ids_to_remove:
      if nid in node.abuts: del node.abuts[nid]
    found_ids_this_scan = set(found_nodes_buffer.keys())
    for nid, abut in node.abuts.items():
      if nid in found_ids_this_scan:
        continue
      last_seen = float(abut.get('last_seen', 0) or 0)
      if last_seen and now - last_seen <= ABUT_ACTIVE_GRACE_SECONDS:
        continue
      node.abuts[nid]['active'] = False
    for nid, discovered_info in found_nodes_buffer.items():
      abut_data = discovered_info['data']; verified_addresses = discovered_info['found_at']
      if not verified_addresses: continue
      if nid not in node.abuts: node.abuts[nid] = {}
      node.abuts[nid].update(abut_data)
      node.abuts[nid]['addresses'] = [list(addr) for addr in sorted(list(verified_addresses))]
      node.abuts[nid]['active'] = True; node.abuts[nid]['last_seen'] = now
    current_ip_to_id_map = {tuple(addr): nid for nid, data in node.abuts.items() if data.get('active') for addr in data.get('addresses', [])}
    for abut_id, abut_data in node.abuts.items():
      if 'abut_nodes' not in abut_data: continue
      node.abuts[abut_id]['abut_nodes'] = {
        n_of_n_id: n_of_n_data for n_of_n_id, n_of_n_data in abut_data.get('abut_nodes', {}).items()
        if n_of_n_data and not any(tuple(a) in current_ip_to_id_map and current_ip_to_id_map[tuple(a)] != n_of_n_id for a in n_of_n_data.get('addresses', []))
      }
    inactive_ids_to_remove = {nid for nid, data in node.abuts.items() if not data.get('active') and now - data.get('last_seen', 0) > INACTIVE_TIMEOUT_SECONDS}
    for nid in inactive_ids_to_remove: del node.abuts[nid]
    for addr in targets_this_cycle - responsive_addresses:
      if addr in node.scan_targets:
        node.scan_targets[addr]["fails"] = min(MAX_SCAN_FAILS, node.scan_targets[addr].get("fails", 0) + 1)
    for addr in responsive_addresses: node.scan_targets[addr] = {"fails": 0}
    for abut_data in node.abuts.values():
      if not abut_data: continue
      for n_data in list(abut_data.get("abut_nodes", {}).values()) + [abut_data]:
        if not n_data: continue
        for addr_list in n_data.get("addresses", []):
          addr_tuple = tuple(addr_list)
          if all(addr_tuple) and addr_tuple not in node.scan_targets:
            node.scan_targets[addr_tuple] = {"fails": 0}

async def discovery_loop(app):
  await asyncio.sleep(5)
  scan_counter = 0; node = app['node']
  while True:
    try:
      scan_counter += 1
      is_full_scan = node.scan_mode == 'full' and (scan_counter == 1 or scan_counter % 12 == 0)
      await discover_and_update_nodes(app, full_scan=is_full_scan)
    except asyncio.CancelledError: break
    except (OSError, AttributeError, TypeError): pass
    except Exception as e:
      debug and frame(f"Error in discovery loop: {e}", "RED")
    await asyncio.sleep(DISCOVERY_INTERVAL_SECONDS)

def add_cors_headers(response):
  response.headers['Access-Control-Allow-Origin'] = '*'
  response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
  response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
  return response

async def handle_get_root(request):
  node = request.app['node']
  primary_addr = node.identity.get("addresses", [])
  primary_host = primary_addr[0][0] if primary_addr else request.host.split(":")[0]
  primary_port = primary_addr[0][1] if primary_addr else request.app.get('port', default_port)
  enc_badge = f'<span style="color:#4caf50">🔒 Noise_XX encrypted</span>' if node.identity.get("encrypted_ws_enabled") else '<span style="color:#aaa">unencrypted</span>'
  pubkey_row = f'<tr><td>Public Key</td><td><code>{node.s_pub.hex()}</code></td></tr>' if node.s_pub else ''
  html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Node: {node.id[:8]}</title>
  <style>:root{{--bg:#20232a;--fg:#e0e0e0;--pri:#8e44ad;--acc:#bb86fc;--sur:#282c34;--bdr:#3a3f4b;--ok:#4caf50;--err:#e53935}}
  body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:2rem}}
  h2,h3{{border-left:6px solid var(--pri);padding-left:1rem;margin-top:2rem}}
  table{{width:100%;border-collapse:collapse;margin:1.5rem 0}}
  th{{background:var(--sur);color:var(--acc);font-weight:600;text-transform:uppercase;border-bottom:2px solid var(--pri)}}
  td{{background:#1c1f26}}th,td{{padding:12px;border:1px solid var(--bdr)}}
  .ok{{color:var(--ok);font-weight:bold}}.err{{color:var(--err)}}
  code{{background:#2e2e2e;color:var(--acc);padding:3px 6px;border-radius:4px;font-family:monospace}}</style></head>
  <body><h2>Node: <b>{node.id}</b> &nbsp; {enc_badge}</h2>
  <p><b>{node.hostname}</b> running <b>{node.script_name}</b> v{node.identity['version']}</p>
  <table><tr><td>Addresses</td><td>{"<br>".join(f"{ip}:{port}" for ip,port in node.identity.get("addresses",[]))}</td></tr>
  {pubkey_row}
  <tr><td>WS endpoint</td><td><code>ws://{primary_host}:{primary_port}{WS_PATH}</code></td></tr></table>
  <h3>Capabilities ({len(node.identity['capabilities'])})</h3>
  <table><tr><th>Function</th></tr>{''.join(f"<tr><td>{c}</td></tr>" for c in sorted(node.identity['capabilities']))}</table>
  <h3>Abuts ({len(node.abuts)})</h3>
  <table><tr><th>ID</th><th>Status</th><th>Addresses</th><th>Hostname</th><th>Version</th><th>Enc</th></tr>
  {''.join(f"<tr><td>{nid}</td><td><span class='{'ok' if nd.get('active') else 'err'}'>{'Active' if nd.get('active') else 'Inactive'}</span></td><td>{nd.get('addresses')}</td><td>{nd.get('hostname','?')}</td><td>{nd.get('version','?')}</td><td>{'🔒' if nd.get('encrypted_ws_enabled') else ''}</td></tr>" for nid,nd in sorted(node.abuts.items()))}
  </table></body></html>"""
  return add_cors_headers(web.Response(text=html, content_type='text/html'))

async def handle_preflight(request):
  return add_cors_headers(web.Response())

async def handle_get_status(request):
  node = request.app['node']
  async with node.lock:
    response_data = copy.deepcopy(node.identity)
    my_abut_ids = set(node.abuts.keys())
    clean_abuts = copy.deepcopy(node.abuts)
    for abut_id, abut_data in clean_abuts.items():
      if 'abut_nodes' in abut_data and isinstance(abut_data['abut_nodes'], dict):
        abut_data['abut_nodes'] = {nid: nd for nid, nd in abut_data['abut_nodes'].items() if nid != node.id and nid not in my_abut_ids}
    response_data["abut_nodes"] = clean_abuts
    response_data["islands"] = _local_joined_islands(request.app, node)
    response_data["visible_islands"] = _visible_islands(request.app, node)
    response_data["stream_peer_count"] = request.app.get('stream_pool').stats().get("peer_count", 0) if request.app.get('stream_pool') else 0
    response_data["healthy"] = True; response_data["busy"] = node.lock.locked(); response_data["result"] = None
  return add_cors_headers(web.json_response(response_data))

async def handle_post_rpc(request):
  node = request.app['node']
  try:
    payload = await request.json()
  except json.JSONDecodeError:
    return add_cors_headers(web.json_response({"result": [_format_response(node.id, None, status="Failed", error="Invalid JSON")]}, status=400))
  if debug: frame([f"RPC Request:", json.dumps(payload, indent=2, ensure_ascii=False)], "ORANGE")
  call_results = await asyncio.gather(*[_process_single_call(request.app, p) for p in payload]) if isinstance(payload, list) else [await _process_single_call(request.app, payload)]
  response_data = copy.deepcopy(node.identity)
  response_data.pop("capabilities", None); response_data.pop("addresses", None)
  response_data["result"] = call_results
  return add_cors_headers(web.json_response(response_data, dumps=lambda d: json.dumps(d, default=str)))

async def _rpc_response_data(app, payload):
  node = app['node']
  call_results = await asyncio.gather(*[_process_single_call(app, p) for p in payload]) if isinstance(payload, list) else [await _process_single_call(app, payload)]
  response_data = copy.deepcopy(node.identity)
  response_data.pop("capabilities", None); response_data.pop("addresses", None)
  response_data["result"] = call_results
  return response_data

async def _handle_ws_event(app, envelope):
  node = app['node']
  payload = envelope.get("payload") or {}
  if not isinstance(payload, dict):
    return {"ok": False, "error": "invalid event payload"}
  target_id = payload.get("id", "auto")
  if target_id not in ("auto", node.id):
    return {"ok": False, "ignored": True, "target_id": target_id}
  call_name = payload.get("call")
  if not call_name:
    return {"ok": False, "error": "missing call"}
  args = payload.get("args", [])
  kwargs = payload.get("kwargs", {})
  return await run_local_function(node.local_functions, call_name, args, kwargs)

async def _ws_plain_loop(app, ws):
  node = app['node']
  async for msg in ws:
    if msg.type == aiohttp.WSMsgType.TEXT:
      try: payload = json.loads(msg.data)
      except json.JSONDecodeError:
        await ws.send_json({"result": [_format_response(node.id, None, status="Failed", error="Invalid JSON")]}); continue
      if isinstance(payload, dict) and payload.get("type") == "rpc":
        request_id = payload.get("request_id")
        response_data = await _rpc_response_data(app, payload.get("payload"))
        await ws.send_json({"type": "rpc_result", "request_id": request_id, "payload": response_data.get("result") or []}, dumps=lambda d: json.dumps(d, default=str))
        continue
      if isinstance(payload, dict) and payload.get("type") == "event":
        result = await _handle_ws_event(app, payload)
        if payload.get("want_ack"):
          await ws.send_json({"type": "event_ack", "event_id": payload.get("event_id"), "payload": result}, dumps=lambda d: json.dumps(d, default=str))
        continue
      response_data = await _rpc_response_data(app, payload)
      await ws.send_json(response_data, dumps=lambda d: json.dumps(d, default=str))
    elif msg.type == aiohttp.WSMsgType.ERROR:
      debug and frame(f"WS error: {ws.exception()}", "RED"); break

async def _ws_secure_loop(app, ws):
  node = app['node']
  try:
    noise = _NoiseXX(False, node.s_priv, node.s_pub)
    m1 = await asyncio.wait_for(ws.receive(), timeout=CALL_TIMEOUT)
    noise.read_msg(m1.data)
    await ws.send_bytes(noise.write_msg())
    m3 = await asyncio.wait_for(ws.receive(), timeout=CALL_TIMEOUT)
    noise.read_msg(m3.data)
    if not _check_trust(node, noise.rs):
      await ws.close(); return
    debug and frame(f"Secure WS: handshake ok, peer={noise.rs.hex()[:16]}...", "DGREEN")
  except Exception as e:
    debug and frame(f"Noise handshake failed: {e}", "RED"); return
  async for raw in ws:
    if raw.type == aiohttp.WSMsgType.BINARY:
      try:
        payload = json.loads(noise.dec(raw.data))
      except Exception as e:
        await ws.send_bytes(noise.enc(json.dumps({"error": "decrypt failed"}).encode())); continue
      if isinstance(payload, dict) and payload.get("type") == "rpc":
        response_data = await _rpc_response_data(app, payload.get("payload"))
        await ws.send_bytes(noise.enc(json.dumps({"type": "rpc_result", "request_id": payload.get("request_id"), "payload": response_data.get("result") or []}, default=str).encode()))
        continue
      if isinstance(payload, dict) and payload.get("type") == "event":
        result = await _handle_ws_event(app, payload)
        if payload.get("want_ack"):
          await ws.send_bytes(noise.enc(json.dumps({"type": "event_ack", "event_id": payload.get("event_id"), "payload": result}, default=str).encode()))
        continue
      response_data = await _rpc_response_data(app, payload)
      await ws.send_bytes(noise.enc(json.dumps(response_data, default=str).encode()))
    elif raw.type == aiohttp.WSMsgType.ERROR:
      debug and frame(f"Secure WS error: {ws.exception()}", "RED"); break

async def handle_websocket(request):
  node = request.app['node']
  protocols = ('zignode-secure', 'zignode') if (crypto_enable and node.s_priv) else ('zignode',)
  ws = web.WebSocketResponse(protocols=protocols)
  await ws.prepare(request)
  proto = getattr(ws, 'ws_protocol', None) or getattr(ws, 'protocol', None)
  debug and frame(f"WS client connected (proto={proto})", "LBLUE")
  if proto == 'zignode-secure':
    await _ws_secure_loop(request.app, ws)
  else:
    await _ws_plain_loop(request.app, ws)
  debug and frame("WS client disconnected", "ORANGE")
  return ws

async def handle_get_favicon(request):
  return add_cors_headers(web.Response(body=favicon_data, content_type='image/x-icon'))

def _is_local(request):
  return request.remote in ('127.0.0.1', '::1', '::ffff:127.0.0.1')

async def handle_mgmt_register(request):
  if not _is_local(request): return web.json_response({"error": "local only"}, status=403)
  node = request.app['node']
  try:
    data = await request.json()
    name = data.get('name'); code = data.get('code')
    if not name or not code: return web.json_response({"error": "missing name or code"}, status=400)
    ns = {}
    exec(compile(code, f'<register:{name}>', 'exec'), ns)
    func = ns.get(name)
    if not inspect.isfunction(func): return web.json_response({"error": f"function '{name}' not found in code"}, status=400)
    node.local_functions[name] = func
    node.identity['capabilities'] = list(node.local_functions.keys())
    frame(f"Registered function: {name}", "DGREEN")
    return web.json_response({"ok": True, "registered": name, "capabilities": node.identity['capabilities']})
  except Exception as e:
    return web.json_response({"error": str(e)}, status=500)

async def handle_mgmt_unregister(request):
  if not _is_local(request): return web.json_response({"error": "local only"}, status=403)
  node = request.app['node']
  try:
    data = await request.json()
    name = data.get('name')
    if name not in node.local_functions: return web.json_response({"error": f"'{name}' not registered"}, status=404)
    del node.local_functions[name]
    node.identity['capabilities'] = list(node.local_functions.keys())
    frame(f"Unregistered function: {name}", "ORANGE")
    return web.json_response({"ok": True, "unregistered": name, "capabilities": node.identity['capabilities']})
  except Exception as e:
    return web.json_response({"error": str(e)}, status=500)

async def handle_mgmt_list(request):
  if not _is_local(request): return web.json_response({"error": "local only"}, status=403)
  node = request.app['node']
  return web.json_response({"capabilities": node.identity['capabilities']})

async def handle_cfgread(request):
  app = request.app; cfg = app.get('config', {})
  if not _is_local(request):
    try: secret = (await request.json()).get('secret')
    except Exception: return web.json_response({"error": "invalid request"}, status=400)
    if not cfg.get('remote_secret') or secret != cfg['remote_secret']:
      return web.json_response({"error": "unauthorized"}, status=403)
  path = app.get('config_path')
  if not path: return web.json_response({"error": "no config loaded"}, status=404)
  try:
    new_cfg = json.load(open(path))
    app['config'] = new_cfg; app['config_sum'] = _checksum(path)
    _apply_plugins(app['node'], new_cfg.get('plugins', []))
    return web.json_response({"ok": True, "capabilities": app['node'].identity['capabilities']})
  except Exception as e:
    return web.json_response({"error": str(e)}, status=500)

async def on_startup(app):
  global _ACTIVE_APP
  if comm_enable:
    app['client_session'] = aiohttp.ClientSession()
    app['stream_pool'] = ZignodeStreamPool(app['client_session'], ws_path=WS_PATH, request_timeout=CALL_TIMEOUT, logger=_streams_logger())
    node = app['node']
    if scan_enable and node.scan_mode != 'disabled':
      app['discovery_task'] = asyncio.create_task(discovery_loop(app))
    if app.get('config_path'):
      app['config_watcher_task'] = asyncio.create_task(config_watcher(app))
    app['island_task'] = asyncio.create_task(island_maintenance_loop(app))
  _ACTIVE_APP = app
  _sd_notify("READY=1")

async def on_cleanup(app):
  global _ACTIVE_APP
  for key in ('discovery_task', 'config_watcher_task', 'island_task'):
    if app.get(key):
      app[key].cancel()
      try: await app[key]
      except asyncio.CancelledError: pass
  if app.get('stream_pool'):
    await app['stream_pool'].close()
  if 'client_session' in app:
    await app['client_session'].close()
  if _ACTIVE_APP is app:
    _ACTIVE_APP = None

def auto(external_locals=None, ip=None, port=None, manual_node_list=None, debug=None, scan=None, not4share=None, name=None, config=None):
  cfg, config_path = _load_config(config)
  _ip   = ip   if ip   is not None else cfg.get('ip',   default_ip)
  _port = port if port is not None else cfg.get('port', default_port)
  _name = name or cfg.get('name')
  _scan = scan or cfg.get('scan', 'full')
  _debug = debug if debug is not None else cfg.get('debug', False)
  _manual = manual_node_list if manual_node_list is not None else [tuple(x) for x in cfg.get('manual_nodes', [])]
  globals()['debug'] = _debug
  globals()['MANUAL_NODE_LIST'] = _manual
  if not comm_enable:
    frame("Communication disabled: 'aiohttp' not found.", "RED"); return
  if crypto_enable:
    s_priv = nb.randombytes(32)
    s_pub = nb.crypto_scalarmult_base(s_priv)
  else:
    s_priv = s_pub = None
  internal_not_for_share = [
    'split_long_string', 'get_computer_name', 'get_all_lan_ips', 'auto',
    'on_startup', 'on_cleanup', 'handle_preflight', 'handle_get_root',
    'handle_get_status', 'handle_post_rpc', 'handle_get_favicon',
    'handle_websocket', 'handle_mgmt_register', 'handle_mgmt_unregister', 'handle_mgmt_list',
    'handle_cfgread', 'discover_and_update_nodes', 'discovery_loop', 'scan_port_wrapper',
    'check_node_status_wrapper', 'run_local_function', 'config_watcher',
    'island_maintenance_loop', '_rpc_response_data', '_handle_ws_event', '_emit_via_app',
    '_send_request', '_send_request_ws', '_send_request_http', '_send_request_secure_ws',
    '_process_single_call', '_format_response', '_broadcast',
    'Node', 'add_cors_headers', '_is_local', '_ws_plain_loop', '_ws_secure_loop',
    '_check_trust', '_sd_notify', '_apply_plugins', '_import_plugin',
    '_resolve_plugin', '_load_config', '_checksum',
    '_active_app', '_supports_streams', '_streams_logger',
    'emit', 'stream_stats', 'islands', 'island_state',
  ]
  if not4share: internal_not_for_share.extend(not4share)
  shareable_functions = {}
  if external_locals:
    shareable_functions = {n: f for n, f in external_locals.items() if inspect.isfunction(f) and n not in internal_not_for_share and not n.startswith('_')}
  node = Node(shareable_functions, scan_mode=_scan, name=_name, s_priv=s_priv, s_pub=s_pub)
  _apply_plugins(node, cfg.get('plugins', []))
  node.core_functions = set(node.local_functions.keys())

  frame([
    f"     \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m Hello! My name is \033[33m{node.script_name} \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
    f"          Node ID     : \033[35m{node.id}\033[34m",
    f"          Version     : \033[92m{node.identity['version']}\033[34m",
    f"          Config      : \033[93m{config_path or 'none'}\033[34m",
    f"          Encryption  : \033[{'92' if node.s_pub else '91'}m{'Noise_XX_25519_ChaChaPoly_BLAKE2b' if node.s_pub else 'disabled'}\033[34m",
    f"          Scan/Comm   : \033[93m{'enabled' if scan_enable and comm_enable else 'disabled'}\033[34m",
    f"          Started at  : \033[96m{datetime.datetime.fromtimestamp(start_time).strftime('%Y_%m_%d %H:%M:%S')}\033[39m",
  ], "BLUE", 70)
  app = web.Application()
  app['node'] = node; app['port'] = _port
  app['config'] = cfg; app['config_path'] = config_path
  app['config_sum'] = _checksum(config_path) if config_path else None
  _ensure_island_runtime(app)

  async def broadcast(func_name, args=None, kwargs=None, target_ids=None, include_self=False):
    session = app.get('client_session')
    if not session: app['client_session'] = aiohttp.ClientSession(); session = app['client_session']
    return await _broadcast(node, session, func_name, args, kwargs, target_ids, include_self)

  async def signal(func_name, args=None, kwargs=None, target_ids=None, include_self=False):
    return await broadcast(func_name, args=args, kwargs=kwargs, target_ids=target_ids, include_self=include_self)

  async def emit_cap(call, args=None, kwargs=None, target_ids=None, include_self=False, metadata=None):
    return await _emit_via_app(app, call, args=args, kwargs=kwargs, target_ids=target_ids, include_self=include_self, metadata=metadata)

  def stream_stats_cap():
    pool = app.get('stream_pool')
    return pool.stats() if pool else {"peers": {}, "peer_count": 0}

  def island_list():
    return _list_islands(app, node)

  def island_get(island_id):
    return _get_island(app, island_id)

  async def island_put(snapshot, advertise=False, target_ids=None):
    island_snapshot, changed = _put_island(app, node, snapshot)
    result = {"changed": changed, "island": island_snapshot}
    if changed and advertise:
      result["sync"] = await island_sync(island_id=island_snapshot["id"], target_ids=target_ids)
    return result

  async def island_join(
    island=None,
    island_id=None,
    name=None,
    kind="generic",
    config=None,
    runtime=None,
    mode="active",
    meta=None,
    advertise=False,
    target_ids=None,
  ):
    island_snapshot = _join_island(
      app,
      node,
      island=island,
      island_id=island_id,
      name=name,
      kind=kind,
      config=config,
      runtime=runtime,
      mode=mode,
      meta=meta,
    )
    result = {"island": island_snapshot}
    if advertise:
      result["sync"] = await island_sync(island_id=island_snapshot["id"], target_ids=target_ids)
    return result

  async def island_leave(island_id, advertise=False, target_ids=None):
    island_snapshot = _leave_island(app, node, island_id)
    result = {"island": island_snapshot}
    if island_snapshot and advertise:
      result["sync"] = await island_sync(island_id=island_id, target_ids=target_ids)
    return result

  async def island_update_config(island_id, config, name=None, advertise=False, target_ids=None):
    island_snapshot = _update_island_config(app, node, island_id, config, name=name)
    result = {"island": island_snapshot}
    if advertise:
      result["sync"] = await island_sync(island_id=island_id, target_ids=target_ids)
    return result

  async def island_update_runtime(island_id, runtime, merge=True, advertise=False, target_ids=None):
    island_snapshot = _update_island_runtime(app, node, island_id, runtime, merge=merge)
    result = {"island": island_snapshot}
    if advertise:
      result["sync"] = await island_sync(island_id=island_id, target_ids=target_ids)
    return result

  async def island_touch(island_id, mode=None, meta=None):
    return _touch_island_member(app, node, island_id, mode=mode, meta=meta)

  async def island_claim_token(island_id, token_name="admin", owner_id=None, ttl_ms=5000, force=False, meta=None, advertise=False, target_ids=None):
    result = _claim_island_token(app, node, island_id, token_name=token_name, owner_id=owner_id, ttl_ms=ttl_ms, force=force, meta=meta)
    if advertise and result.get("ok"):
      result["sync"] = await island_sync(island_id=island_id, target_ids=target_ids)
    return result

  async def island_release_token(island_id, token_name="admin", owner_id=None, force=False, advertise=False, target_ids=None):
    result = _release_island_token(app, node, island_id, token_name=token_name, owner_id=owner_id, force=force)
    if advertise and result.get("ok"):
      result["sync"] = await island_sync(island_id=island_id, target_ids=target_ids)
    return result

  async def island_sync(island_id=None, target_ids=None, include_self=False):
    snapshots = []
    if island_id:
      snap = _get_island(app, island_id)
      if snap:
        snapshots.append(snap)
    else:
      for summary in _local_joined_islands(app, node):
        snap = _get_island(app, summary["id"])
        if snap:
          snapshots.append(snap)
    if not snapshots:
      return []
    session = app.get('client_session')
    if not session: app['client_session'] = aiohttp.ClientSession(); session = app['client_session']
    sync_results = []
    for snap in snapshots:
      members = [member_id for member_id in (snap.get("members") or {}).keys() if member_id != node.id]
      wanted = target_ids if target_ids is not None else members
      if not wanted and not include_self:
        continue
      sync_results.extend(await _broadcast(node, session, "island_put", kwargs={"snapshot": snap}, target_ids=wanted, include_self=include_self))
    return sync_results

  shareable_functions['broadcast'] = broadcast
  shareable_functions['signal'] = signal
  shareable_functions['emit'] = emit_cap
  shareable_functions['stream_stats'] = stream_stats_cap
  shareable_functions['island_list'] = island_list
  shareable_functions['island_get'] = island_get
  shareable_functions['island_put'] = island_put
  shareable_functions['island_join'] = island_join
  shareable_functions['island_leave'] = island_leave
  shareable_functions['island_update_config'] = island_update_config
  shareable_functions['island_update_runtime'] = island_update_runtime
  shareable_functions['island_touch'] = island_touch
  shareable_functions['island_claim_token'] = island_claim_token
  shareable_functions['island_release_token'] = island_release_token
  shareable_functions['island_sync'] = island_sync
  node.local_functions = shareable_functions
  node.core_functions.update({'broadcast', 'signal', 'emit', 'stream_stats', 'island_list', 'island_get', 'island_put', 'island_join', 'island_leave', 'island_update_config', 'island_update_runtime', 'island_touch', 'island_claim_token', 'island_release_token', 'island_sync'})
  node.identity["capabilities"] = list(shareable_functions.keys())
  app.router.add_get("/", handle_get_root)
  app.router.add_get("/status", handle_get_status)
  app.router.add_get("/status/", handle_get_status)
  app.router.add_get(WS_PATH, handle_websocket)
  app.router.add_get("/favicon.ico", handle_get_favicon)
  app.router.add_post("/", handle_post_rpc)
  app.router.add_post("/mgmt/register", handle_mgmt_register)
  app.router.add_post("/mgmt/unregister", handle_mgmt_unregister)
  app.router.add_get("/mgmt/list", handle_mgmt_list)
  app.router.add_get("/cfgread", handle_cfgread)
  app.router.add_post("/cfgread", handle_cfgread)
  app.router.add_route("OPTIONS", "/{tail:.*}", handle_preflight)
  app.on_startup.append(on_startup)
  app.on_cleanup.append(on_cleanup)
  frame(f"Listening on: http://{_ip}:{_port}", "GREEN")
  try:
    web.run_app(app, host=_ip, port=_port, print=None)
  except OSError as e:
    frame(f"{'Port already in use' if 'already in use' in str(e).lower() else 'OS error'}: {e}", "RED")
  except (KeyboardInterrupt, SystemExit):
    pass
  finish_time = time.time()
  frame([
    "        \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m My name is \033[33m" + node.script_name + "\033[39m goodbye. \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
    "      Started run   : \033[93m " + datetime.datetime.fromtimestamp(start_time).strftime("%Y_%m_%d %H:%M:%S"),
    "      Finished run  : \033[93m " + datetime.datetime.fromtimestamp(finish_time).strftime("%Y_%m_%d %H:%M:%S"),
    "      Elapsed time  : \033[93m " + str(datetime.timedelta(seconds=int(finish_time - start_time)))
  ], "ORANGE", 70)

if __name__ == '__main__':
  def add(a, b): return a + b
  auto(locals())
