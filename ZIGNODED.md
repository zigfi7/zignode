# zignoded — daemon extension of zignode

## Pliki

| Plik | Opis |
|------|------|
| `libs/zignoded.py` | Główny rdzeń runtime i demona |
| `libs/zignode.py` | Cienki shim kompatybilności dla `import zignode` |
| `libs/zignode_utils.py` | Opcjonalny plugin: msg, notif, speak, frame |
| `zignode.config` | Przykładowy config |

`libs/zignode.py` nie ma już osobnego silnika. Re-eksportuje publiczne API z `libs/zignoded.py`.

---

## Co dodaje zignoded vs zignode.py

### 1. Szyfrowanie node2node — Noise_XX_25519_ChaChaPoly_BLAKE2b

| Warstwa | Implementacja |
|---------|---------------|
| Handshake | Noise_XX — mutual auth, obie strony poznają klucze statyczne |
| DH | X25519 (libsodium/PyNaCl) |
| AEAD | ChaCha20-Poly1305 IETF (12-byte nonce, little-endian counter) |
| KDF | BLAKE2b-64 keyed mode jako HMAC, HKDF-2 |
| Trust | In-memory session keys — `node.trusted_keys` / `node.revoked_keys` |

**Klucze efemeryczne** — generowane przy każdym starcie (jak node UUID), brak I/O na dysk.

**Transport:** ten sam endpoint `/ws`, subprotocol negocjowany przez `Sec-WebSocket-Protocol`:
- `zignode-secure` → Noise_XX handshake (3 binary frames) + szyfrowane JSON RPC
- `zignode` / brak → plain WS (fallback dla legacy 25.2 nodów)

**Priorytet połączeń w `_send_request`:**
1. Encrypted WS — jeśli target ma `encrypted_ws_enabled: true`
2. Plain WS — jeśli `ws_enabled: true`
3. HTTP POST — ostatni fallback

**Nowe pola w identity:**
```json
{
  "version": "25.3d",
  "encrypted_ws_enabled": true,
  "public_key": "hex_x25519_ephemeral_pub"
}
```

### 2. Config-driven plugin system z live reload

**`zignode.config`** (JSON, auto-detect w katalogu skryptu):
```json
{
  "name":          "mój_node",
  "port":          8635,
  "scan":          "full",
  "manual_nodes":  [],
  "plugins":       ["zignode_utils", "/opt/moje/funkcje.py"],
  "debug":         false,
  "remote_secret": null
}
```

Parametry w config są **domyślnymi** — explicit args w `auto()` mają priorytet.

**Live reload przez checksum SHA-256:**
- Background task sprawdza sumę kontrolną pliku co 5 sekund
- Gdy się zmieni → automatyczny reload pluginów (dodanie/usunięcie/zmiana)
- `node.core_functions` (broadcast, signal, user funcs) nigdy nie są usuwane przez plugin unload

**Plugin** = dowolny plik `.py`. Każda publiczna funkcja (bez `_`) staje się capability.

### 3. API zarządzania (localhost only)

```
GET/POST /cfgread                          — reload konfiga i pluginów
GET      /mgmt/list                        — lista capabilities
POST     /mgmt/register  {"name","code"}   — rejestracja funkcji przez kod
POST     /mgmt/unregister {"name"}         — wyrejestrowanie
```

`/cfgread` remote (przez zaszyfrowany kanał): wymaga `{"secret": "..."}` zgodnego z `remote_secret` w configu.

### 4. zignode_utils.py — wydzielony plugin

Zawiera: `msg()`, `notif()` (desktop notifications), `speak()` (TTS), `frame()`.
Działa jako standalone plugin — załaduj przez config, nie trzeba modyfikować zignoded.py.

### 5. systemd integration

`_sd_notify("READY=1")` przez `NOTIFY_SOCKET` po starcie serwera.

### 6. Wyspy i pooled WebSocket streams są częścią core

- replicated island state, membership i token lease są trzymane bezpośrednio w `zignoded.py`
- pooled plain-JSON WS obsługuje zarówno `emit`, jak i request/reply RPC
- proxied ścieżki mogą korzystać z tego samego transportu zamiast otwierać nowe WS per call
- warstwa wysp jest logiczną orkiestracją nad dynamiczną siatką node'ów; wyspa ma pozostać stabilna jako funkcja/system, nawet gdy fizyczne nody dołączają i odpadają

### 7. Discovery: fizyczna topologia vs warstwa wysp

Discovery nadal działa w dwóch torach:
- **znane adresy**: `scan_targets`, `manual_nodes` i `127.0.0.1`
- **nowe adresy z LAN**: okresowy full scan sieci

Aktualny przepływ:
1. znane targety są sprawdzane bezpośrednio przez `GET /status`
2. tylko nowe adresy z pełnego skanu LAN przechodzą najpierw przez szybki port-check
3. top-level `abut_nodes` z `/status` to bezpośredni sąsiedzi
4. zagnieżdżone `abut_nodes` wewnątrz sąsiada są traktowane jako kandydaci 2-hop i ich adresy wracają do `scan_targets`
5. pełny scan LAN nadal działa okresowo, ale nie blokuje odświeżania znanych peerów

To rozdzielenie jest istotne dla systemów typu swarm/grid:
- discovery utrzymuje **fizyczną topologię i control-plane**
- wyspy utrzymują **logiczne grupy funkcji i stan rozproszony**

Ważna poprawka z `2026-03-21`:
- wcześniejszy gate `open_connection(..., timeout=0.2)` dla wszystkich targetów potrafił fałszywie odrzucać zdrowe nody pod obciążeniem ruchu z warstwy wysp
- skutkiem było okresowe zerowanie `node.abuts`, mimo że te same hosty odpowiadały poprawnie na `/status`
- od teraz znane peery nie są odcinane przez pre-scan portu; szybki port-check pozostał tylko dla nowych adresów odkrywanych przez full scan
- concurrency dla port-scan i `/status` jest rozdzielone osobno, żeby ograniczyć zapychanie event loop

---

## Użycie

```bash
# Uruchomienie — auto-detect zignode.config w CWD
cd ~/projects/zignode && python3 libs/zignoded.py

# Z explicit configiem
python3 libs/zignoded.py --config /etc/zignoded/prod.config  # (przez auto(config=...))

# Jako lib (jak zignode)
from zignoded import auto
def my_func(x): return x * 2
auto(locals())                          # bez configa
auto(locals(), config='zignode.config') # z configiem

# Reload pluginów po zmianie configa
curl http://localhost:8635/cfgread

# Rejestracja funkcji w locie (localhost)
curl -X POST http://localhost:8635/mgmt/register \
  -H Content-Type:application/json \
  -d '{"name":"ping","code":"def ping(): return \"pong\""}'

# Sprawdź capabilities
curl http://localhost:8635/mgmt/list
```

---

## Zależności systemowe (Arch — pacman)

```
python-pynacl      (libsodium: X25519, ChaCha20-Poly1305)
python-aiohttp     (HTTP + WS server/client)
python-netifaces2  (LAN scanning)
```

Bez venv. Brak dodatkowych zależności dla core — `hashlib`, `importlib`, `struct` to stdlib.

---

## Znane uwagi

- `scan='disabled'` wyłącza pętlę odkrywania całkowicie (w tym manual_node_list). Dla testów używaj domyślnego `scan='full'`.
- aiohttp 3.13+: `ws.ws_protocol` zamiast `ws.protocol` — obsłużone przez `getattr` fallback.
- Sieć /22 (~1022 hostów): pierwsze odkrycie po ~10s od startu (5s sleep + ~5s port scan).
- Każdy encrypted RPC call = nowy Noise_XX handshake (brak persistent sessions) — TODO dla przyszłości.
- Join/leave pasywny (polling 30s), pełny detect disconnect do ~125s — TODO: keepalive na persistent sessions.

---

## Stan wdrożenia

| Data       | Commit | Co zrobiono |
|------------|--------|-------------|
| 2026-03-12 | 7778715 | Napisano zignoded.py v25.3d — Noise_XX, mgmt API, plugin loading |
| 2026-03-12 | 11f89ba | Fix: ws_protocol dla aiohttp 3.13+ |
| 2026-03-12 | 9cfbeb8 | Fix: debug log dla secure WS fallback |
| 2026-03-12 | 34a4392 | Docs: ZIGNODED.md |
| 2026-03-12 | 6136348 | Refactor: klucze efemeryczne w pamięci, usunięto I/O dla crypto identity |
| 2026-03-12 | b98b01f | Feat: config-driven plugin system, live reload przez SHA-256 checksum, zignode_utils.py |

## Testy (den1 — den-ziglab-13, aarch64, Python 3.14, PyNaCl 1.6.2, aiohttp 3.13)

- Noise_XX handshake math ✅
- Encrypted WS RPC (test_enc_full.py) ✅
- Node widzi 6 legacy nodów (25.2) w sieci ✅
- Encrypted RPC node→node ✅
- Dynamic register/unregister ✅
- Config live reload (checksum watcher) ✅
- zignode_utils.py jako plugin (msg, frame) ✅
