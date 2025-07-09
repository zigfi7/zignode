#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, platform, subprocess, inspect, time, datetime, uuid, json, base64, re, ipaddress, copy, asyncio, random
debug=False
try:
    from aiohttp import web
    import aiohttp
    comm_enable = True
except ImportError:
    comm_enable = False
try:
    import netifaces
    scan_enable = True
except ImportError:
    scan_enable = False
start_time = time.time()
__MyName__ = os.path.split(sys.argv[0])[1]
system_type = platform.system()
default_ip = "0.0.0.0"
default_port = 8635
MANUAL_NODE_LIST = []
MAX_SCAN_FAILS = 16
CALL_TIMEOUT = 15 
INACTIVE_TIMEOUT_SECONDS = 95 
cc = {
    "RESET": "\033[0m", "NOCOLOR": "\033[39m", "BLACK": "\033[30m", "DRED": "\033[31m", "DGREEN": "\033[32m",
    "ORANGE": "\033[33m", "BLUE": "\033[34m", "VIOLET": "\033[35m", "CYAN": "\033[36m", "LGRAY": "\033[37m",
    "DGRAY": "\033[90m", "RED": "\033[91m", "GREEN": "\033[92m", "YELLOW": "\033[93m", "DBLUE": "\033[94m",
    "PINK": "\033[95m", "LBLUE": "\033[96m", "WHITE": "\033[97m"
}
favicon_data = base64.b64decode("AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQAMAAAAAAAAAAIAAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO2AAIBZAAAAAAAAAACAAIBkgACA/4AAgPqAAIDYgACA2IAAgNiAAIDYgACA2IAAgNiAAIDYgACA/AAAgP+AAICjgACABwAAAAAAAAAAAAAAAIAAgOmAAID/gACAPIAAgAJAAEACQABAAkAAQAKAAIACgACAJoAAgNCAAIDwgACATgAAAAAAAAAAAAAAAAAAAACAAIAygACA/AAAgO4AAAAAAAAAAAAAAAAAAAAAAAAAAIAAgIWAAID/gACAjgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgMeAAID/gACAawAAAAAAAAAAAAAAAIAAgEGAAIDogACA24AAgDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAIASgACA/AAAgPuAAIAGAAAAAIAAgAOAAICYgACA/AAAgHsAAAAAAAAAAEAAQBIAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgJaAAID/gACAoQAAAACAAIBdgACA+IAAgL+AAIAYAAAAAAAAAACAAICDgACA6IAAgAwAAAAAAAAAAAAAAACAAIAEgACA+YAAgP+AAIAmgACAsoAAgPyAAIBnAAAAAAAAAACAAIA6gACA5IAAgN6AAIA0AAAAAAAAAAAAAAAAAAAAAIAAgGGAAID/gACA9IAAgP2AAICjgACABwAAAAAAAAAAgACAkoAAgP+AAIB+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACA6YAAgP+AAIDxgACAT4AAgAKAAIACgACAUYAAgPOAAIDJgACAHgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgDKAAID/gACA/AAAgNmAAIDYgACA2IAAgN2AAID/gACAbwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACAvoAAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgAw4AAgA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAJAAEAPQABAD0AAQA9AAEAPQABAD0AAQA8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAP//AAAABwAAgAcAAJ/PAADPjwAAz58AAOc/AADjOQAA8nkAAPhzAAD48wAA/AcAAPwHAAD//wAA//8AAA==")
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
        output_lines.append(f"│ {cc['NOCOLOR']}{sline}{padding}{cc[COLOR]} │")
    output_lines.append(cc[COLOR] + "└" + "─" * frame_width + "┘" + cc["RESET"])
    output_string = "\n".join(output_lines)
    if display:
        print(output_string)
    return output_string
def get_computer_name():
    try:
        return subprocess.check_output(["hostname"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return platform.node()
notif = None
try:
    if platform.system() == "Windows":
        import plyer
        def notif_win(message):
            plyer.notification.notify(title=__MyName__, message=str(message), app_icon=None, timeout=15)
        notif = notif_win
    elif platform.system() == "Linux":
        import notify2
        notify2.init("zignode")
        def notif_linux(message):
            notify2.Notification(__MyName__, str(message)).show()
        notif = notif_linux
except ImportError: pass
speak = None
try:
    if platform.system() == "Windows":
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        def speak_win(message, language="English"):
            speaker.Speak(str(message))
        speak = speak_win
    elif platform.system() == "Linux":
        if subprocess.run(["which", "RHVoice-test"], capture_output=True).returncode == 0:
            def speak_rhvoice(message, language="English"):
                voice = "Alicja" if language.lower() == "polish" else "lyubov"
                subprocess.run(["RHVoice-test", "-p", voice], input=str(message), text=True, capture_output=True)
            speak = speak_rhvoice
except (ImportError, FileNotFoundError): pass
def msg(message, language="English"):
    """Displays a message in a frame and optionally speaks it."""
    frame(str(message))
    if speak:
        try: speak(message, language)
        except: pass
    if notif:
        try: notif(message)
        except: pass
    return f'Message processed: {message}'
async def run_local_function(scope, func_name, params):
    """Executes a function available on the local node."""
    params = [params] if not isinstance(params, list) else params
    try:
        target_func = scope.get(func_name)
        if not target_func: raise ValueError(f"Function '{func_name}' not found")
        if asyncio.iscoroutinefunction(target_func):
            return await target_func(*params)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, target_func, *params)
    except Exception as e:
        return {"error": f"Execution of '{func_name}' failed: {e}"}
def _format_response(id, value, status="Success", routed_by=None, error=None):
    """Standardizes the structure for all call responses."""
    response = {"id": id, "status": status, "value": value}
    if routed_by:
        response["routed_by"] = routed_by
    if error:
        response["value"] = None
        response["error"] = error
    return response
async def _send_request(session, target_node_data, payload):
    """Sends a POST request to a target node and returns the result list."""
    if not target_node_data.get("addresses"):
        return [_format_response(payload.get('id', 'unknown'), None, status="Failed", error="Target node has no known address.")]
    target_ip, target_port = target_node_data["addresses"][0]
    url = f"http://{target_ip}:{target_port}/"
    target_id = payload.get('id', 'unknown')
    try:
        async with session.post(url, json=payload, timeout=CALL_TIMEOUT) as response:
            response.raise_for_status()
            try:
                response_json = await response.json()
                if "result" in response_json and isinstance(response_json.get("result"), list):
                    return response_json["result"]
                else:
                    return [_format_response(target_id, response_json)]
            except (aiohttp.ContentTypeError, json.JSONDecodeError):
                return [_format_response(target_id, None, status="Success")]
    except aiohttp.ClientResponseError as e:
        return [_format_response(target_id, None, status="Failed", error=f"HTTP Error: {e.status} {e.message}")]
    except asyncio.TimeoutError:
        return [_format_response(target_id, None, status="Failed", error="Request timed out.")]
    except Exception as e:
        return [_format_response(target_id, None, status="Failed", error=f"Request failed: {e}")]
async def _process_single_call(app, payload):
    """Contains the main logic for executing a single function call."""
    node = app['node']
    session = app['client_session']
    func_name = payload.get("call")
    if not func_name:
        return _format_response(node.id, None, status="Failed", error="Missing 'call' parameter.")
    args = payload.get("args", [])
    target_id = payload.get("id", "auto")
    if target_id != "auto":
        if target_id == node.id:
            result = await run_local_function(node.local_functions, func_name, args)
            return _format_response(node.id, result)
        async with node.lock:
            abuts_copy = dict(node.abuts)
        if target_id in abuts_copy and abuts_copy[target_id].get("active"):
            target_node_data = abuts_copy[target_id]
            result_list = await _send_request(session, target_node_data, payload)
            return result_list[0] if result_list else _format_response(target_id, None, status="Failed", error="No response from direct abut.")
        for abut_id, abut_data in abuts_copy.items():
            if not abut_data.get("active"): continue
            abut_nodes = abut_data.get("abut_nodes", {})
            if target_id in abut_nodes:
                proxy_node_data = abut_data
                result_list = await _send_request(session, proxy_node_data, payload)
                if not result_list:
                    return _format_response(target_id, None, status="Failed", error="No response from proxy node.")
                final_result = result_list[0]
                final_result["routed_by"] = abut_id
                return final_result
        return _format_response(target_id, None, status="Failed", error="Target node not found or inactive.")
    if func_name in node.local_functions:
        result = await run_local_function(node.local_functions, func_name, args)
        return _format_response(node.id, result)
    async with node.lock:
        abuts_copy = dict(node.abuts)
    direct_candidates = [
        nid for nid, ndata in abuts_copy.items()
        if ndata.get("active") and func_name in ndata.get("capabilities", [])
    ]
    if direct_candidates:
        chosen_id = random.choice(direct_candidates)
        payload["id"] = chosen_id
        target_node_data = abuts_copy[chosen_id]
        result_list = await _send_request(session, target_node_data, payload)
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
        proxy_id = chosen_route["proxy_id"]
        final_target_id = chosen_route["target_id"]
        payload["id"] = final_target_id
        proxy_node_data = abuts_copy[proxy_id]
        result_list = await _send_request(session, proxy_node_data, payload)
        if not result_list:
             return _format_response(final_target_id, None, status="Failed", error="No response from proxy for routed call.")
        final_result = result_list[0]
        final_result["routed_by"] = proxy_id
        return final_result
    return _format_response("auto", None, status="Failed", error=f"No node found with capability '{func_name}'.")
class Node:
    def __init__(self, local_functions):
        self.id = str(uuid.uuid4())
        self.start_time = time.time()
        self.script_name = os.path.basename(sys.argv[0])
        self.hostname = get_computer_name()
        self.abuts = {}
        self.scan_targets = {}
        self.lock = asyncio.Lock()
        self.local_functions = local_functions
        self.identity = {
            "id": self.id, "myname": self.script_name, "version": "23.1-smarter-cleanup",
            "type": "complex" if comm_enable and scan_enable else "simple",
            "started": self.start_time, "hostname": self.hostname,
            "platform": platform.system(), "capabilities": list(self.local_functions.keys()),
            "addresses": []
        }
def get_all_lan_ips():
    if not scan_enable: return []
    ips = set()
    try:
        for interface in netifaces.interfaces():
            if_addresses = netifaces.ifaddresses(interface).get(netifaces.AF_INET)
            if if_addresses:
                for addr_info in if_addresses:
                    ip, netmask = addr_info.get("addr"), addr_info.get("netmask")
                    if ip and netmask and not ip.startswith("127."):
                        try:
                            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                            if network.prefixlen >= 19 and network.num_addresses < 8192:
                                ips.update(str(host) for host in network.hosts())
                        except ValueError: continue
    except Exception as e:
        frame(f"Could not scan network interfaces: {e}", "RED")
    return list(ips)
async def scan_port_wrapper(sem, ip, port):
    async with sem:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=0.2)
            writer.close()
            await writer.wait_closed()
            return (ip, port)
        except (asyncio.TimeoutError, OSError):
            return None
async def check_node_status_wrapper(sem, session, ip, port):
    async with sem:
        url = f"http://{ip}:{port}/status"
        try:
            async with session.get(url, timeout=5.0) as response:
                if response.status == 200:
                    data = await response.json()
                    node_id = data.get("id")
                    if node_id:
                        return node_id, data, (ip, port)
        except (asyncio.TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
            pass
    return None, None, None
async def discover_and_update_nodes(app, full_scan=False):
    node = app['node']
    session = app['client_session']
    sem = asyncio.Semaphore(512)
    async with node.lock:
        scan_targets_to_check = {addr for addr, data in node.scan_targets.items() if data.get("fails", 0) < MAX_SCAN_FAILS}
        if full_scan:
            if debug:
                frame("Starting full network discovery...", "DGREEN")
            scan_targets_to_check.update(node.scan_targets.keys())
            if scan_enable:
                lan_ips = await asyncio.to_thread(get_all_lan_ips)
                for ip in lan_ips:
                    scan_targets_to_check.add((ip, default_port))
    targets_this_cycle = scan_targets_to_check.union(set(MANUAL_NODE_LIST))
    targets_this_cycle.add(("127.0.0.1", default_port))
    port_scan_tasks = [scan_port_wrapper(sem, ip, port) for ip, port in targets_this_cycle]
    open_hosts = {res for res in await asyncio.gather(*port_scan_tasks) if res}
    status_check_tasks = [check_node_status_wrapper(sem, session, ip, port) for ip, port in open_hosts]
    status_results = await asyncio.gather(*status_check_tasks)
    found_nodes_buffer = {}
    responsive_addresses = set()
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
        old_addr_map = {tuple(addr): nid for nid, data in node.abuts.items() for addr in data.get('addresses', [])}
        ids_to_remove = set()
        for nid, discovered_info in found_nodes_buffer.items():
            for addr in discovered_info.get('found_at', set()):
                if addr in old_addr_map and old_addr_map[addr] != nid:
                    ids_to_remove.add(old_addr_map[addr])
        for nid in ids_to_remove:
            if nid in node.abuts:
                if debug:
                    frame(f"Removing conflicted abut {nid[:8]}", "ORANGE")
                del node.abuts[nid]
        found_ids_this_scan = set(found_nodes_buffer.keys())
        for nid in node.abuts:
            if nid not in found_ids_this_scan:
                node.abuts[nid]['active'] = False
        for nid, discovered_info in found_nodes_buffer.items():
            abut_data = discovered_info['data']
            verified_addresses = discovered_info['found_at']
            if not verified_addresses: continue
            if nid not in node.abuts:
                node.abuts[nid] = {}
            node.abuts[nid].update(abut_data)
            node.abuts[nid]['addresses'] = [list(addr) for addr in sorted(list(verified_addresses))]
            node.abuts[nid]['active'] = True
            node.abuts[nid]['last_seen'] = time.time()
        current_ip_to_id_map = {
            tuple(addr): nid 
            for nid, data in node.abuts.items() 
            if data.get('active') 
            for addr in data.get('addresses', [])
        }
        for abut_id, abut_data in node.abuts.items():
            if 'abut_nodes' not in abut_data: continue
            original_n_of_n = abut_data.get('abut_nodes', {})
            clean_n_of_n = {} 
            for n_of_n_id, n_of_n_data in original_n_of_n.items():
                is_stale = False
                for addr_list in n_of_n_data.get('addresses', []):
                    addr = tuple(addr_list)
                    if addr in current_ip_to_id_map and current_ip_to_id_map[addr] != n_of_n_id:
                        is_stale = True
                        break 
                if not is_stale:
                    clean_n_of_n[n_of_n_id] = n_of_n_data
            node.abuts[abut_id]['abut_nodes'] = clean_n_of_n
        inactive_ids_to_remove = set()
        for nid, data in node.abuts.items():
            if not data.get('active'):
                if time.time() - data.get('last_seen', 0) > INACTIVE_TIMEOUT_SECONDS:
                    inactive_ids_to_remove.add(nid)
        for nid in inactive_ids_to_remove:
            if nid in node.abuts:
                if debug:
                    frame(f"Removing timed-out abut {nid[:8]}", "ORANGE")
                del node.abuts[nid]
        failed_addresses = targets_this_cycle - responsive_addresses
        for addr in failed_addresses:
            if addr in node.scan_targets:
                node.scan_targets[addr]["fails"] = node.scan_targets[addr].get("fails", 0) + 1
        for addr in responsive_addresses:
            node.scan_targets[addr] = {"fails": 0}
        for abut_data in node.abuts.values():
            nodes_to_scan_for = list(abut_data.get("abut_nodes", {}).values())
            nodes_to_scan_for.append(abut_data)
            for n_data in nodes_to_scan_for:
                for addr_list in n_data.get("addresses", []):
                    addr_tuple = tuple(addr_list)
                    if all(addr_tuple) and addr_tuple not in node.scan_targets:
                        node.scan_targets[addr_tuple] = {"fails": 0}
    active_count = sum(1 for n in node.abuts.values() if n.get('active'))
    if debug:
        frame(f"Discovery complete. Known abuts: {len(node.abuts)} ({active_count} active).", "GREEN")
async def discovery_loop(app):
    await asyncio.sleep(5)
    scan_counter = 0
    while True:
        try:
            scan_counter += 1
            is_full_scan = (scan_counter == 1 or scan_counter % 12 == 0)
            await discover_and_update_nodes(app, full_scan=is_full_scan)
        except asyncio.CancelledError:
            break
        except Exception as e:
            frame(f"Error in discovery loop: {e}", "RED")
        await asyncio.sleep(30)
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
async def handle_get_root(request):
    node = request.app['node']
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Node: {node.id[:8]}</title>
        <style>
            :root {{
                --background-color: #1e1e1e;
                --text-color: #e0e0e0;
                --primary-color: #bb86fc;
                --secondary-color: #3700b3;
                --surface-color: #2a2a2a;
                --border-color: #333333;
                --success-color: #03dac6;
                --error-color: #cf6679;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: var(--background-color);
                color: var(--text-color);
                margin: 0;
                padding: 2rem;
            }}
            main {{
                margin: auto;
            }}
            h2, h3 {{
                color: var(--primary-color);
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 10px;
                font-weight: 500;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                margin-bottom: 30px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            th, td {{
                border: 1px solid var(--border-color);
                padding: 12px 15px;
                text-align: left;
                word-break: break-all;
            }}
            th {{
                background-color: var(--secondary-color);
                color: var(--text-color);
                font-weight: 600;
            }}
            td {{
                background-color: var(--surface-color);
            }}
            b {{
                color: var(--text-color);
                font-weight: 600;
            }}
            code {{
                background-color: var(--border-color);
                color: var(--primary-color);
                padding: 3px 6px;
                border-radius: 4px;
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
            }}
            .header-container {{
                display: flex;
                align-items: center;
                gap: 25px;
                margin-bottom: 2rem;
                flex-wrap: wrap;
            }}
            .header-container svg {{
                filter: drop-shadow(0 0 8px rgba(187, 134, 252, 0.5));
                flex-shrink: 0;
            }}
            .status-active {{
                color: var(--success-color);
                font-weight: bold;
            }}
            .status-inactive {{
                color: var(--error-color);
            }}
            a {{
                color: var(--primary-color);
            }}
        </style>
    </head>
    <body>
        <main>
            <div class="header-container">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="90" height="90">
                    <path fill="#bb86fc" stroke="#1e1e1e" stroke-width="0.5" d="M4.75 8L12 4l7.25 4v8L12 20l-7.25-4V8Z"/>
                </svg>
                <div>
                    <h2>Node ID: <b>{node.id}</b></h2>
                    <p><b>{node.hostname}</b> running <b>{node.script_name}</b></p>
                </div>
            </div>

            <h3>API</h3>
            <p>Send a <code>POST</code> request to <code>/</code> with a JSON body. Can be a single call object or a list of calls.</p>
            <p>Example: <code>{{"call": "msg", "args": ["Hello"], "id": "node_id_or_auto"}}</code></p>
            
            <h3>Local Capabilities ({len(node.identity['capabilities'])})</h3>
            <table>
                <tr><th>Function Name</th></tr>
                {''.join(f"<tr><td>{cap}</td></tr>" for cap in sorted(node.identity['capabilities']))}
            </table>

            <h3>Abuts ({len(node.abuts)})</h3>
            <table>
                <tr><th>ID</th><th>Status</th><th>Addresses (My PoV)</th><th>Hostname</th><th>Version</th></tr>
                {''.join(
                    f"<tr>"
                    f"<td>{nid}</td>"
                    f"<td><span class='status-{'active' if nd.get('active') else 'inactive'}'>{'Active' if nd.get('active') else 'Inactive'}</span></td>"
                    f"<td>{nd.get('addresses')}</td>"
                    f"<td>{nd.get('hostname','N/A')}</td>"
                    f"<td>{nd.get('version','N/A')}</td>"
                    f"</tr>"
                    for nid, nd in sorted(node.abuts.items())
                )}
            </table>
        </main>
    </body>
    </html>
    """
    return add_cors_headers(web.Response(text=html, content_type='text/html'))
    return add_cors_headers(web.Response(text=html, content_type='text/html'))
async def handle_get_status(request):
    node = request.app['node']
    async with node.lock:
        response_data = copy.deepcopy(node.identity)
        my_abut_ids = set(node.abuts.keys())
        clean_abuts = copy.deepcopy(node.abuts)
        for abut_id, abut_data in clean_abuts.items():
            if 'abut_nodes' in abut_data and isinstance(abut_data['abut_nodes'], dict):
                abut_data['abut_nodes'] = {
                    nid: ndata for nid, ndata in abut_data['abut_nodes'].items()
                    if nid != node.id and nid not in my_abut_ids
                }
        response_data["abut_nodes"] = clean_abuts
        response_data["healthy"] = True
        response_data["busy"] = node.lock.locked()
        response_data["result"] = None
    return add_cors_headers(web.json_response(response_data))
async def handle_post_rpc(request):
    node = request.app['node']
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        error_result = [_format_response(node.id, None, status="Failed", error="Invalid JSON")]
        return add_cors_headers(web.json_response({"result": error_result}, status=400))
    if isinstance(payload, list):
        tasks = [_process_single_call(request.app, p) for p in payload]
        call_results = await asyncio.gather(*tasks)
    else:
        call_results = [await _process_single_call(request.app, payload)]
    response_data = copy.deepcopy(node.identity)
    response_data.pop("capabilities", None)
    response_data.pop("addresses", None)
    response_data["result"] = call_results
    return add_cors_headers(web.json_response(response_data))
async def handle_get_favicon(request):
    return add_cors_headers(web.Response(body=favicon_data, content_type='image/x-icon'))
async def on_startup(app):
    if comm_enable:
        app['client_session'] = aiohttp.ClientSession()
        if scan_enable:
            app['discovery_task'] = asyncio.create_task(discovery_loop(app))
async def on_cleanup(app):
    if 'discovery_task' in app and app.get('discovery_task'):
        app['discovery_task'].cancel()
        try: await app['discovery_task']
        except asyncio.CancelledError: pass
    if 'client_session' in app:
        await app['client_session'].close()
def auto(external_locals=None, ip=default_ip, port=default_port, manual_node_list=MANUAL_NODE_LIST, debug_mode=False):
    global debug 
    debug = debug_mode
    MANUAL_NODE_LIST=manual_node_list;
    if not comm_enable:
        frame("Communication disabled: 'aiohttp' library not found.", "RED")
        return
    not_for_share = [
        'split_long_string', 'get_computer_name', 'get_all_lan_ips', 'auto', 
        'on_startup', 'on_cleanup', 'handle_get_root', 'handle_get_status', 
        'handle_post_rpc', 'handle_get_favicon', 'discover_and_update_nodes', 
        'discovery_loop', 'scan_port_wrapper', 'check_node_status_wrapper', 
        'run_local_function', '_send_request', '_process_single_call', '_format_response', 
        'Node', 'add_cors_headers',
        'notif_win', 'notif_linux', 'speak_win', 'speak_rhvoice'
    ]
    shareable_functions = {}
    if external_locals:
        shareable_functions = {
            name: func for name, func in external_locals.items()
            if inspect.isfunction(func) and name not in not_for_share and not name.startswith('_')
        }
    shareable_functions['msg'] = msg
    shareable_functions['frame'] = frame
    if notif:
        shareable_functions['notif'] = notif
    if speak:
        shareable_functions['speak'] = speak
    node = Node(shareable_functions)
    start_message = [
    f"       \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m Hello! My name is \033[33m{node.script_name} \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
    f"         Node ID    : \033[35m{node.id}\033[34m",
    f"         Version    : \033[92m{node.identity['version']}\033[34m",
    f"         Scan/Comm  : \033[93m{'enabled' if scan_enable and comm_enable else 'disabled'}\033[34m",
    f"         Started at : \033[96m{datetime.datetime.fromtimestamp(start_time).strftime('%Y_%m_%d %H:%M:%S')}\033[39m"]
    frame(start_message, "BLUE", 70)
    app = web.Application()
    app['node'] = node
    app['port'] = port
    app.router.add_get("/", handle_get_root)
    app.router.add_get("/status", handle_get_status)
    app.router.add_get("/status/", handle_get_status)
    app.router.add_get("/favicon.ico", handle_get_favicon)
    app.router.add_post("/", handle_post_rpc)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    frame(f"Listening on: http://{ip}:{port}", "GREEN")
    try:
        web.run_app(app, host=ip, port=port, print=None if not debug else True, access_log=None if not debug else sys.stdout)
    except (KeyboardInterrupt, SystemExit):
        pass
    finish_time = time.time()
    finish_message = [
        "       \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m My name is \033[33m"
        + node.script_name +
        "\033[39m goodbye. \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==",
        "    Started run  : \033[93m " +
        datetime.datetime.fromtimestamp(start_time).strftime("%Y_%m_%d %H:%M:%S"),
        "    Finished run : \033[93m " +
        datetime.datetime.fromtimestamp(finish_time).strftime("%Y_%m_%d %H:%M:%S"),
        "    Elapsed time : \033[93m " +
        str(datetime.timedelta(seconds=int(finish_time - start_time)))
    ]
    print ("")
    frame(finish_message, "ORANGE", 70)
if __name__ == '__main__':
    def add(a, b):
        return a + b
    auto(locals())
