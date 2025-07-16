# 🔌 Zignode – Zero-Effort, Self-Discovering RPC for Python (and Beyond)

**Zignode** is a lightweight framework that turns any script (Python and potentially others) into a smart, networked node — often with just a single line of code in Python.
Forget about manual server configuration and request handling. Simply expose your functions and let the nodes discover, communicate, and collaborate automatically on your local network.

This project was born from the practical needs of an electronics enthusiast: how to easily control devices connected to a Raspberry Pi (or similar systems) without writing a dedicated server for each project?
**Zignode is the answer**, offering a universal and instant solution.

Although originally implemented in Python, the **Zignode protocol** is language-agnostic. Support for other platforms (e.g., Arduino/C++, Node.js) is actively being explored.

---

## ✨ Key Features

* ⚙️ **Effortless Python Integration**
  Just call `zignode.auto(locals())` at the end of your script — and all your functions become available on the network.

* 🌐 **Automatic Network Discovery**
  Nodes scan the local network to find others — no config files, no central server required.

* 🧐 **Intelligent Function Routing**
  Zignode builds a "mesh mind" across the network. If a function isn't available locally, it automatically forwards the call to the right node — even via 2-hop neighbors.

* 🎯 **Targeted or Automatic Execution**
  Call a specific node (by ID) or let the network choose the best node for the job.

* 🧱 **Built-in Web UI**
  Each node hosts a web interface with its function list, status info, and discovered neighbors.

* 🛎️ **Integrated Utilities**
  Optional built-in helpers: `msg()`, `notif()`, `speak()` for notifications and TTS (RHVoice/Linux).

* 🦦 **Lightweight & Interoperable**
  Fully async (`aiohttp`, `netifaces2`), using standard HTTP/JSON — works great with ESP32, MicroPython, and is extendable to C++/Arduino/Node.js.

---

## ⚙️ Requirements

* Python **3.8+**
* Automatically installs:

  * `aiohttp`
  * `netifaces2`

---

## 📦 Installation

```bash
pip install zignode
```

---

## 🧪 Usage Example (Python)

```python
#!/usr/bin/python
# -*- coding: utf-8 -*-

import zignode

def set_servo_position(position: int):
    print(f"SERVO: Setting position to {position} degrees.")
    return f"Servo position set to {position}."

def read_temperature():
    temp = 23.5
    print(f"SENSOR: Read temperature: {temp}°C")
    return {"temperature": temp, "unit": "Celsius"}

if __name__ == '__main__':
    zignode.auto(
        external_locals=locals(),
        debug_mode=True,
        manual_node_list=[('192.168.1.101', 8635)]
    )
```

---

## 📡 How It Works

Zignode creates a peer-to-peer network where every node is equal.

**Startup**

* The node starts a local HTTP server and begins scanning the network.

**Discovery**

* On port `8635`, Zignode discovers others, exchanging available functions and neighbors.

**Execution**

* When a call is made:

  1. If the function exists locally → execute.
  2. Else → check neighbors.
  3. If needed → 2-hop route via neighbor’s neighbors.

This builds a self-healing, mesh-style RPC network.

---

## 📬 How to Call Functions

You can use any HTTP client (`curl`, `requests`, Postman) to call functions on any node.

### 1. Call a local or auto-routed function:

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"call": "set_servo_position", "args": [90]}' \
http://localhost:8635/
```

### 2. Call a function on a specific node (by ID):

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"call": "read_temperature", "id": "a1b2c3d4-..."}' \
http://localhost:8635/
```

### 3. Send a message using `msg()`:

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"call": "msg", "args": ["Message from the network!"]}' \
http://localhost:8635/
```

---

## 🗐 Web UI

Each node automatically hosts a web page at `http://<ip>:8635/`, showing:

* Node ID
* Available functions
* Discovered neighbors
* Optional logs

*(Screenshot coming soon)*

---

## 🚧 Roadmap

* [ ] Authentication & API tokens
* [ ] Optional encryption (Fernet or TLS)
* [ ] Multicast ZeroConf support
* [ ] WebSocket-based push events
* [ ] Native MicroPython/ESP8266 bridge
* [ ] Arduino/C++ protocol client
* [ ] Node.js-compatible Zignode client

---

## 🧑‍💻 Authors & Credits

* Concept, architecture & integration: **Zigfi** ([GitHub](https://github.com/zigfi7))
* Early implementations & sync version: written by Zigfi
* Code support provided by AI assistants:

  * **Gemini** (Google)
  * **ChatGPT** (OpenAI)
  * **Claude** (Anthropic)
  * **Mistral**, **Tulu3** and others
* Protocol and structure are designed to be **human-readable and language-agnostic**

Feedback, forks and PRs welcome!

---

## 📜 License

This project is licensed under the **Apache 2.0 License**. See [LICENSE](./LICENSE) for details.
