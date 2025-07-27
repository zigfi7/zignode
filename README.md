🔌 Zignode – Ultra-Fast, Self-Discovering RPC for Python (and Beyond)

Tired of writing a dedicated server every time you want to control a device over the network? Zignode is a lightweight tool that transforms any Python script into an intelligent, networked node—often with just one import and a single line of code.

Forget about configuration or handling HTTP requests. Just expose your functions, and Zignode does the rest: nodes automatically discover each other, share their capabilities, and collaborate on remote function calls within your LAN. It's a decentralized RPC that just works.
🧭 The KISS Philosophy: Simplicity That Works

Zignode was born from the need to bridge the power of low-level electronics with the convenience of network control—without unnecessary complexity. Following the KISS (Keep It Simple, Stupid) principle, the tool gets out of your way, letting you focus on what truly matters.

    For Hobbyists: Control your Raspberry Pi, ESP32, or robotics projects from any computer on your network—without writing a server.

    For Developers and Testers: Build decentralized testing environments and distribute tasks without a central broker.

    For Everyone: Create a self-organizing network of smart devices that simply communicate with each other.

✨ Ideal Use Cases

    Home Automation: A script on your laptop calls turn_on_lights() on a Raspberry Pi in another room.

    Robotics and Electronics: A robot's main unit delegates read_distance() or set_motor_speed() to microcontrollers.

    Automated Testing: Run tests across multiple platforms (Linux, Windows, mobile) by calling functions on remote nodes.

    Simple Distributed Computing: Distribute tasks (e.g., image processing, data validation) across your LAN.

🚀 Key Features

    ⚙️ Effortless Integration: Just add zignode.auto(locals()) at the end of your Python script, and you're online.

    🌐 Automatic Discovery: Nodes scan the network and find each other. No configuration, central server, or files needed.

    🧠 Decentralized Routing: Zignode builds a "mesh mind" and forwards requests to the appropriate nodes, even through other neighbors (2-hop routing).

    🎯 Flexible Calls: Supports positional (args) and keyword (kwargs) arguments, targeting by ID, or searching by capability.

    🖥️ Cross-Platform: Works on Linux, Windows, and macOS without extra configuration.

    🦦 Lightweight and Interoperable: Based on asyncio and aiohttp, using standard HTTP/JSON. The protocol is compatible with ESP32, MicroPython, and Arduino.

    🔍 Configurable Scanning:

        full: scans entire subnets.

        basic: scans only a defined list of addresses.

        disabled: passive mode, no scanning.
        The manual address list accepts hostnames, IPv4, IPv6, and custom ports.

    🐞 Debug Mode: Detailed logging of scans, network messages, and internal node events.

    🔖 Custom Node Name: An optional name parameter, e.g., zignode.auto(locals(), name="cmd_zignode").

⚙️ How It Works

Zignode creates a peer-to-peer network where all nodes are equal:

    Start: A node launches a lightweight aiohttp server and (depending on the mode) scans the local network on port 8635.

    Discovery: After finding neighbors, it exchanges its function list and its list of known neighbors. This process is repeated periodically, making the network self-healing.

    Execution:

        Is the function local? → It's executed immediately.

        Not local? → The node asks its direct neighbors.

        Still not found? → It asks its neighbors if their neighbors have the function (2-hop routing).

        Once found, the result is returned along the same path.

        If the function is not found anywhere on the network, an error is returned.

The result: a reliable, mesh RPC network with no single point of failure.
📦 Installation and Usage

Requirements: Python 3.8+

pip install zignode

Example (my_device.py):

#!/usr/bin/python
# -*- coding: utf-8 -*-
import zignode

def set_servo(position: int, speed: int = 100):
    print(f"SERVO: Moving to {position} degrees at speed {speed}.")
    return f"OK: Servo set to {position}."

def read_temperature():
    temp = 23.5
    print(f"SENSOR: Read temperature: {temp}C")
    return {"temperature": temp, "unit": "Celsius"}

if __name__ == '__main__':
    zignode.auto(
        external_locals=locals(),
        debug=True
    )

Run it and you're done:

python my_device.py

📬 Calling Functions

You can use any HTTP client (curl, requests, Postman):

1. Positional arguments (args):

curl -X POST -H "Content-Type: application/json" \
-d '{"call": "set_servo", "args": [90]}' \
http://localhost:8635/

2. Keyword arguments (kwargs):

curl -X POST -H "Content-Type: application/json" \
-d '{"call": "set_servo", "kwargs": {"position": 180, "speed": 50}}' \
http://localhost:8635/

🌐 Ecosystem and Integrations

    Web Interface: Each node serves a simple web panel at http://<ip>:8635/ with a list of functions, neighbors, and status. Thanks to CORS support, you can easily create web applications that communicate with the Zignode network.

    HTML Client: The repository includes a ready-to-use HTML client that, when connected to any active node, displays an interactive network map and allows you to call functions on any device.

    lite Version: A synchronous zignode-lite version is available, which requires no external dependencies (beyond the standard Python distribution). It operates in passive mode and is ideal for simple applications.

    Arduino Implementation: An implementation for the Wemos D1 (ESP8266) with WiFi and display support also exists. It acts as a passive node capable of executing commands.

    Practical Implementation: The project has been field-tested on a Raspberry Pi controlling 16 servos (PCA9685), with a dedicated web interface for real-time control over the Zignode network.

🚧 Roadmap
🧱 Near-Term Plans and Considerations:

    WebSocket Implementation: To increase network responsiveness and enable active event pushing.

    Optional Security Layer: Mechanisms (e.g., tokens) to secure the network from unauthorized access. Crucial for commercial or public network applications.

    Timers and Background Tasks: The ability to run long-running tasks without blocking the node, with start and stop options.

    MQTT Support: Considered for implementation as an additional, optional communication method.

🌌 Long-Term Vision:

    Distributed Memory: Mechanisms for sharing state and data between nodes.

    Functional Groups: Creating virtual "islands" with distributed memory and computing power for more complex tasks.

    Abstract Logical Layers: The ability to build more complex, multi-level systems.

    Direct Protocols: Implementation of non-network communication methods (e.g., via serial ports) for controlling robot swarms.

🧑‍💻 The Story of Zignode

Zignode wasn't created in a vacuum. It's the result of years of work with electronics, robotics, and test automation. It all started with a frustration: controlling hardware is fun, but writing the same network layers for it over and over? Tedious.

I thought: why can't I just call a function on another device as easily as I do it locally?

So I created a system that is:

    Decentralized (no single point of failure)

    Self-organizing (zero configuration)

    Intuitive (works right away)

Zignode is a tool that respects your time and simplifies distributed systems.
👥 Authors and Acknowledgments

    Concept, architecture, implementation: Zigfi

    Protocol: designed to be human-readable and language-agnostic.

    AI Support: with help from models by Google, OpenAI, Anthropic, and others.

All feedback, forks, and PRs are welcome!
📜 License

This project is licensed under the Apache 2.0 License. See the LICENSE file for details.