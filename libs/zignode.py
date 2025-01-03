#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, platform, subprocess, inspect, tempfile, time, datetime, uuid, json, base64, io, re, http.server, urllib.parse, ipaddress, threading, random, math, socket, signal, xml.etree.ElementTree as ET

scan_enable = True
comm_enable = True
try:
    import requests
except Exception as e:
    comm_enable = False
try:
    import socks
except Exception as e:
    scan_enable = False
try:
    import netifaces
except Exception as e:
    scan_enable = False
# ──────────────────────────────────────────────────────────────────────────────────────────────────┤ Generic ├────────────
start_time = time.time()
__MyName__ = os.path.split(sys.argv[0])[1]
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
system_type = platform.system()
node = None
default_ip = "0.0.0.0"
default_port = 8635
abut_nodes = {}
caller_locals = None
caller_functions = None

cc = {
    "RESET": "\033[0m",
    "NOCOLOR": "\033[39m",
    "BLACK": "\033[30m",
    "DRED": "\033[31m",
    "DGREEN": "\033[32m",
    "ORANGE": "\033[33m",
    "BLUE": "\033[34m",
    "VIOLET": "\033[35m",
    "CYAN": "\033[36m",
    "LGRAY": "\033[37m",
    "DGRAY": "\033[90m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "DBLUE": "\033[94m",
    "PINK": "\033[95m",
    "LBLUE": "\033[96m",
    "WHITE": "\033[97m",
}


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
        if (
            len(re.sub(r"\033\[\d+m", "", str(current_string)))
            + len(re.sub(r"\033\[\d+m", "", str(word)))
        ) <= max_length:
            current_string += word + " "
        else:
            result_strings.append(current_string.strip())
            current_string = word + " "
    if current_string:
        result_strings.append(current_string.strip())
    return result_strings


def frame(lines="", COLOR="NOCOLOR", frames=25, framemax=92):
    # Characters = "└┘┼─┴├┤┬┌┐│"
    lineslst = True if isinstance(lines, list) else False
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
                    lll = ll if ll > lll else lll
                    linelist.append(ssline)
            else:
                lll = ll if ll > lll else lll
                linelist.append(sline)
    else:
        lines = str(lines)
        ll = len(re.sub(r"\033\[\d+m", "", str(lines)))
        if ll + 2 > framemax:
            sublines = split_long_string(lines, framemax - 2)
            for ssline in sublines:
                ll = len(re.sub(r"\033\[\d+m", "", str(ssline)))
                lll = ll if ll > lll else lll
                linelist.append(ssline)
        else:
            lll = ll if ll > lll else lll
            linelist.append(lines)
    frames = lll + 2

    print(cc[COLOR] + "┌" + "─" * frames + "┐" + cc[COLOR])
    for sline in linelist:
        print(
            "│ "
            + cc["NOCOLOR"]
            + str(sline)
            + " " * (frames - len(re.sub(r"\033\[\d+m", "", str(sline))) - 2)
            + cc[COLOR]
            + " │"
        )
    print(cc[COLOR] + "└" + "─" * frames + "┘" + cc["RESET"])


def start():
    message = [
        "       \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m Hello! My name is \033[33m"
        + __MyName__
        + " \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
        f'         Started run : \033[93m {datetime.datetime.fromtimestamp(start_time).strftime("%Y_%m_%d %H:%M:%S")}',
    ]
    frame(message, "BLUE", 70)


def finish():
    finish_time = time.time()
    message = [
        "       \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m My name is \033[33m"
        + __MyName__
        + "\033[39m goodbye. \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
        "    Started run  : \033[93m "
        + datetime.datetime.fromtimestamp(start_time).strftime("%Y_%m_%d %H:%M:%S"),
        "    Finished run : \033[93m "
        + datetime.datetime.fromtimestamp(finish_time).strftime("%Y_%m_%d %H:%M:%S"),
        "    Elapsed time : \033[93m "
        + str(datetime.timedelta(seconds=int(finish_time - start_time))),
    ]
    frame(message, "ORANGE", 70)


def get_computer_name():
    myname = os.getenv("COMPUTERNAME")
    if myname is not None:
        return myname.strip()
    if myname is not None:
        return myname.strip()
    process = subprocess.Popen(["hostname"], stdout=subprocess.PIPE)
    myname, _ = process.communicate()
    return myname.decode("utf-8").strip()


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Functions Specific ├────────────
# ────────────┤ Notification ├────────────
try:
    if platform.system() == "Windows":
        import plyer

        def notif(message):
            plyer.notification.notify(
                title=__MyName__,
                message=message,
                app_icon=None,
                timeout=15,
            )
            return True

except Exception as e:
    pass

try:
    if platform.system() == "Linux":
        import notify2

        def notif(message):
            notify2.init("")
            notification = notify2.Notification(__MyName__, message)
            notification.show()
            return True

except Exception as e:
    pass

# if not notif:
#   def notif(message):
#     frame ([message],'RED')

# ────────────┤ Speak ├────────────

try:
    if platform.system() == "Windows":
        import win32com.client

        def speak(message, language="English", rate=2.5, volume=80):
            voice = None
            voices = [
                v.GetDescription()
                for v in win32com.client.Dispatch("SAPI.SpVoice").GetVoices()
            ]
            print(voices)
            for vo in voices:
                if "Eng" in vo and "Aria" in vo:
                    voice = vo
                elif language in vo:
                    voice = vo
            for vo in voices:
                if language in vo:
                    voice = vo
            print(f'Selected: {cc["GREEN"]} {voice}{cc["NOCOLOR"]}')
            if voice:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Voice = next(
                    vo for vo in speaker.GetVoices() if vo.GetDescription() == voice
                )
                speaker.Rate = rate
                speaker.Volume = volume
                try:
                    speaker.Speak(message)
                except Exception as e:
                    print(f'{cc["RED"]}Error:{cc["NOCOLOR"]} {e}')
            else:
                print(f'{cc["RED"]}No voice for: {language}{cc["NOCOLOR"]}')
                for vo in voices:
                    print(vo)
                frame([message], "RED")

except Exception as e:
    pass

if platform.system() == "Linux":
    # In linux we will use rhvoice
    try:
        subprocess.run(
            ["which", "RHVoice-test"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def speak(message, language="English", rate=2.5, volume=80):
            if language.lower() == "polish":
                rhvoice_voice = "Alicja"
            elif language.lower() == "english":
                rhvoice_voice = "lyubov"
            else:
                frame([message], "RED")
                return False
            try:
                subprocess.run(
                    [
                        "RHVoice-test",
                        "-p",
                        rhvoice_voice,
                        "-v",
                        str(volume),
                        "-r",
                        str(int(rate * 0.6 * 100)),
                    ],
                    input=message,
                    text=True,
                )
                # time.sleep(0)
                return True
            except Exception as e:
                print(f'{cc["RED"]}Error:{cc["NOCOLOR"]} {e}')

    except subprocess.CalledProcessError:
        pass


def msg(message, language="English"):
    print(message)
    if speak:
        speak(message, language)
    if notif:
        notif(message)


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Runners ├────────────


def getfunctions(vlocals):
    global caller_locals
    caller_locals = vlocals
    caller_functions = [
        name for name, value in caller_locals.items() if inspect.isfunction(value)
    ]
    return caller_functions


def run_function(lf, fname, params):
    params = [str(params)] if not isinstance(params, list) else params
    try:
        target_function = lf.get(fname)
        if target_function is None:
            raise ValueError(f"Function '{fname}' not found in locals")
        result = target_function(*params)
        return result
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Net ├────────────


if comm_enable and scan_enable:

    def msg_abut(*args):
        abut_id = args[0] if len(args) > 0 else None
        call_name = args[1] if len(args) > 1 else None
        call_args = args[2:] if len(args) > 2 else []
        json_in = {"call": call_name, "args": call_args}
        # print (json_in)
        global node
        abut_info = node.identity.get("abut_nodes", {}).get(abut_id, {})
        abut_ip = abut_info.get("ip", "")
        abut_port = abut_info.get("port", "")

        if abut_info and abut_ip and abut_port:
            abut_url = f"http://{abut_ip}:{abut_port}/"
            # print(abut_url)
            headers = {"Content-Type": "application/json"}
            abut_response = None
            try:
                response = requests.post(abut_url, json=json_in, headers=headers)
                response.raise_for_status()
                response_json = response.json()
                abut_response = response_json.get("result", None)
            except requests.exceptions.RequestException as e:
                # print("Error:", e)
                return {"error": str(e)}
            return {abut_id: abut_response}


if comm_enable and scan_enable:

    def test_portopen(host="127.0.0.1", port=8635, timeout=0.5):
        try:
            sock = socket.create_connection((host, port))
            sock.settimeout(timeout)
            sock.close()
            return True
        except Exception as e:
            print(f"{host} Error: {e}")
            return False


if comm_enable and scan_enable:

    def get_node_status(url, max_attempts=10, timeout=2):
        node_id = ""
        for attempt in range(1, max_attempts + 1):
            try:
                #      print(url)
                response = requests.get(url + "/status/", timeout=timeout)
                response.raise_for_status()
                response_json = response.json()
                node_id = response_json.get("id", "")

            except Exception as e:
                # print(f'Url request error: {e}')
                response_json = {}
            if node_id:
                return response_json
        return {}


if comm_enable and scan_enable:

    def scan_lan(port=default_port, timeout=0.002):
        hosts_set = set()
        hosts_open = []
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET)
            if addresses:
                for address in addresses:
                    ip_address = address["addr"]
                    if (
                        ipaddress.ip_address(ip_address).is_private
                        and ip_address != "127.0.0.1"
                    ):
                        network_mask = address["netmask"]
                        network = ipaddress.IPv4Network(
                            f"{ip_address}/{network_mask}", strict=False
                        )
                        lan_ips = set([str(host) for host in network.hosts()])
                        hosts_set.update(lan_ips)
        for hostip in list(hosts_set):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    s.connect((hostip, port))
                    hosts_open.append(hostip)
            except:
                pass
        return hosts_open


if comm_enable and scan_enable:

    def check_health(
        url=f"http://localhost:{default_port}", max_attempts=10, timeout=2
    ):
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url + "/status/", timeout=timeout)
                response.raise_for_status()
                response_json = response.json()
            except requests.exceptions.RequestException as e:
                # print(f'Url request error: {e}')
                response_json = {}

            if response_json and "healthy" in response_json and "busy" in response_json:
                if response_json["healthy"] and not response_json["busy"]:
                    return True
            time.sleep(1)
        else:
            # print(f'Connection failed with {url}')
            return False


if comm_enable and scan_enable:

    def find_net_nodes(port=default_port):
        nodes = {}
        nodes_ip_candidate = scan_lan()
        if test_portopen("127.0.0.1", port):
            nodes_ip_candidate.insert(0, "127.0.0.1")
        for node_ip in nodes_ip_candidate:
            node_status = get_node_status(f"http://{node_ip}:{port}")
            node_id = node_status.get("id", "")
            if node_id:
                node_status["ip"] = node_ip
                node_status["port"] = port
                if "id" in node_status:
                    del node_status["id"]
                if "abut_nodes" in node_status:
                    del node_status["abut_nodes"]
                nodes.setdefault(node_id, node_status)
        # frame(["Found nodes: "] + list(nodes.keys()),'YELLOW')
        return nodes


# ───────────────────────────────────────────────────────────────────────────────────┤ Call functions ├────────────


def autocall(tid, fcall, args):
    args = [str(args)] if not isinstance(args, list) else args

    global caller_locals
    global node

    # print (fcall)
    if fcall in node.identity.get("capabilities", []):
        if tid == node.id and fcall:
            if caller_functions and fcall in caller_functions:
                result = run_function(caller_locals, fcall, args)
            elif fcall in node.capabilities:
                result = run_function(local_variables, fcall, args)
            else:
                result = None
    elif fcall:
        abuts = node.identity.get("abut_nodes", {})
        capable = []
        for abutID, properties in abuts.items():
            if fcall in properties.get("capabilities", []):
                capable.append(abutID)
        if capable:
            print("msg_abut", [capable[0], fcall, *args])
            result = msg_abut(*[capable[0], fcall, *args])
            # .get('result',None)
            return result
    else:
        pass


# ───────────────────────────────────────────────────────────────────────────────────┤ List local functions ├────────────
local_variables = locals()
all_local_functions = [
    name for name, value in local_variables.items() if callable(value)
]
not4share = [
    "split_long_string",
    "start",
    "finish",
    "get_computer_name",
    "getfunctions",
    "run_function",
    "timeout_handler",
    "test_portopen",
    "get_node_status",
    "scan_lan",
    "check_health",
    "find_net_nodes",
    "mkhtml",
    "Node",
    "msg_abut",
    "autocall",
]
local_functions = [
    funkcja for funkcja in all_local_functions if funkcja not in not4share
]

# ───────────────────────────────────────────────────────────────────────────────────┤ HTTP API ├────────────
favicon_data = "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQAMAAAAAAAAAAIAAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO2AAIBZAAAAAAAAAACAAIBkgACA/4AAgPqAAIDYgACA2IAAgNiAAIDYgACA2IAAgNiAAIDYgACA/4AAgP+AAICjgACABwAAAAAAAAAAAAAAAIAAgOmAAID/gACAPIAAgAJAAEACQABAAkAAQAKAAIACgACAJoAAgNCAAIDwgACATgAAAAAAAAAAAAAAAAAAAACAAIAygACA/4AAgO4AAAAAAAAAAAAAAAAAAAAAAAAAAIAAgIWAAID/gACAjgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgMeAAID/gACAawAAAAAAAAAAAAAAAIAAgEGAAIDogACA24AAgDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAIASgACA/4AAgPuAAIAGAAAAAIAAgAOAAICYgACA/4AAgHsAAAAAAAAAAEAAQBIAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgJaAAID/gACAoQAAAACAAIBdgACA+IAAgL+AAIAYAAAAAAAAAACAAICDgACA6IAAgAwAAAAAAAAAAAAAAACAAIAEgACA+YAAgP+AAIAmgACAsoAAgPyAAIBnAAAAAAAAAACAAIA6gACA5IAAgN6AAIA0AAAAAAAAAAAAAAAAAAAAAIAAgGGAAID/gACA9IAAgP2AAICjgACABwAAAAAAAAAAgACAkoAAgP+AAIB+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACA6YAAgP+AAIDxgACAT4AAgAKAAIACgACAUYAAgPOAAIDJgACAHgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgDKAAID/gACA/4AAgNmAAIDYgACA2IAAgN2AAID/gACAbwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACAvoAAgO+AAIDvgACA74AAgO+AAIDvgACAw4AAgA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAJAAEAPQABAD0AAQA9AAEAPQABAD0AAQA8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAP//AAAABwAAgAcAAJ/PAADPjwAAz58AAOc/AADjOQAA8nkAAPhzAAD48wAA/AcAAPwHAAD//wAA//8AAA=="


def mkhtml(node):
    myid = node.id
    index_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>node {myid}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                color: #333;
                margin: 20px;
            }}

            h1 {{
                color: #0066cc;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}

            table, th, td {{
                border: 1px solid #ddd;
            }}

            th, td {{
                padding: 12px;
                text-align: left;
            }}

            th {{
                background-color: #0066cc;
                color: white;
            }}
        </style>
    </head>
    <body>
    <article>
      <h2>Node id: <b>{myid}</b></h2>
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="100" height="100"><path fill="darkviolet" stroke="#000" stroke-width="1.5" d="M4.75 8L12 4l7.25 4v8L12 20l-7.25-4V8Z"/></svg>
      <table>
        <tr><td>Running on PC:</td><td> <b>{get_computer_name()}</b></td></tr>
        <tr><td>Script name:  </td><td> <b>{__MyName__}</b></td></tr>
        <tr><td>Initialized:  </td><td> <b>{datetime.datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")}</b></td></tr>
      </table>
    </article>
    </body>
  </html>
    """
    return index_content


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Node Class ├────────────
class Node:
    _instance = None
    functions_lib = []
    identity = {}
    capabilities = []

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        if comm_enable and scan_enable:
            self.thread = threading.Thread(target=self.process, daemon=True)
            self.thread.start()

        self.id = str(uuid.uuid4())
        self.healthy = True
        self.busy = False
        self.myver = "1.0"
        self.nodes = {}
        self.proxies = None
        self.identity = {}
        self.my_type = "complex" if comm_enable and scan_enable else "simple"
        # master_id = None
        # token = False

        self.identity.update({"id": str(self.id)})
        self.identity.update({"myname": __MyName__})
        self.identity.update({"version": self.myver})
        self.identity.update({"type": self.my_type})
        self.identity.update({"started": start_time})
        self.identity.update({"hostname": get_computer_name()})
        self.identity.update({"platform": system_type})
        self.identity.update({"capabilities": self.capabilities})
        # self.my_type='simple'
        # self.my_type='passive'
        frame(
            [
                f"Node_Init: {self.id}",
                (
                    "Scanning is      : enabled"
                    if scan_enable
                    else "Scanning is      : disabled"
                ),
                (
                    "Communication is : enabled"
                    if comm_enable
                    else "Communication is : disabled"
                ),
            ],
            "PINK",
        )

    def json2json(self, json_in):
        debug = True
        self.json_out = {}
        if debug and json_in:
            print("Received:")
            frame(json.dumps(json_in, indent=2).split("\n"), "ORANGE")
        # ─────────────────────────────────┤ Response Logic ├────────────
        self.json_out.update(self.identity)
        self.json_out.update({"healthy": self.healthy})
        self.json_out.update({"busy": self.busy})
        self.message = json_in.get("message", "")
        self.call = json_in.get("call", "")
        self.args = json_in.get("args", "")
        self.tid = json_in.get("id", self.id)
        self.busy = True
        result = autocall(self.tid, self.call, self.args) if json_in else None
        self.busy = False
        self.json_out.update({"result": result})
        # ─────────────────────────────────┤ / Response Logic ├────────────
        if debug and json_in:
            print("Sending:")
            frame(json.dumps(self.json_out, indent=2).split("\n"), "LBLUE")
        return self.json_out

    def process(self):
        while True:
            time.sleep(2)
            if not self.busy:
                try:
                    nodes = find_net_nodes()
                    neighbors = {
                        zignode: nodes[zignode]
                        for zignode in nodes
                        if zignode != self.id
                    }
                    if neighbors:
                        self.identity["abut_nodes"] = neighbors
                    else:
                        self.identity["abut_nodes"] = {}
                except Exception as e:
                    self.identity["abut_nodes"] = {}
                    print(e)
            time.sleep(18)


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Http Handler ├────────────


class NodeHttp(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.node = kwargs.pop("node", None)
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html", "/index.htm"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(mkhtml(self.node).encode("utf-8"))

            elif self.path in ("/status/, /status"):
                response_data = self.node.json2json({})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode("utf-8"))

            elif self.path == "/favicon.ico":
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.end_headers()
                self.wfile.write(base64.b64decode(favicon_data))
            else:
                self.send_error(404, "Not Found")
        except ConnectionResetError:
            pass

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        try:
            data_json = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON data")
            return
        response_data = self.node.json2json(data_json)
        response_json = json.dumps(response_data)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response_json.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────────────────┤ Session init ├────────────
def init(caller_locals=None):
    global node
    global caller_functions
    node = Node()
    node.capabilities.extend(local_functions)
    if caller_locals:
        caller_functions = getfunctions(caller_locals)
        node.capabilities.extend(caller_functions)


def listen(
    ip=default_ip,
    port=default_port,
):
    global node
    server = http.server.HTTPServer(
        (ip, port), lambda *args, **kwargs: NodeHttp(node=node, *args, **kwargs)
    )
    frame(f"Listening on: http://{ip}:{port}", "GREEN")
    server.serve_forever()


def auto(caller_locals=None):
    start()
    init(caller_locals)
    listen()
    finish()


if __name__ == "__main__":
    auto()
