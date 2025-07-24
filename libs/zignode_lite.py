#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, platform, subprocess, inspect, time, datetime, uuid, json, base64, re, http.server, socket, threading

start_time = time.time()
__MyName__ = os.path.basename(sys.argv[0])
default_ip = "0.0.0.0"
default_port = 8635

node = None
cc = {
  "RESET": "\033[0m", "NOCOLOR": "\033[39m", "BLACK": "\033[30m", "DRED": "\033[31m", "DGREEN": "\033[32m",
  "ORANGE": "\033[33m", "BLUE": "\033[34m", "VIOLET": "\033[35m", "CYAN": "\033[36m", "LGRAY": "\033[37m",
  "DGRAY": "\033[90m", "RED": "\033[91m", "GREEN": "\033[92m", "YELLOW": "\033[93m", "DBLUE": "\033[94m",
  "PINK": "\033[95m", "LBLUE": "\033[96m", "WHITE": "\033[97m"
}
favicon_data = base64.b64decode("AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQA9AAEAPQABAD0AAQAMAAAAAAAAAAIAAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO+AAIDvgACA74AAgO2AAIBZAAAAAAAAAACAAIBkgACA/4AAgPqAAIDYgACA2IAAgNiAAIDYgACA2IAAgNiAAIDYgACA/4AAgP+AAICjgACABwAAAAAAAAAAAAAAAIAAgOmAAID/gACAPIAAgAJAAEACQABAAkAAQAKAAIACgACAJoAAgNCAAIDwgACATgAAAAAAAAAAAAAAAAAAAACAAIAygACA/4AAgO4AAAAAAAAAAAAAAAAAAAAAAAAAAIAAgIWAAID/gACAjgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgMeAAID/gACAawAAAAAAAAAAAAAAAIAAgEGAAIDogACA24AAgDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAIASgACA/4AAgPuAAIAGAAAAAIAAgAOAAICYgACA/4AAgHsAAAAAAAAAAEAAQBIAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgJaAAID/gACAoQAAAACAAIBdgACA+IAAgL+AAIAYAAAAAAAAAACAAICDgACA6IAAgAwAAAAAAAAAAAAAAACAAIAEgACA+YAAgP+AAIAmgACAsoAAgPyAAIBnAAAAAAAAAACAAIA6gACA5IAAgN6AAIA0AAAAAAAAAAAAAAAAAAAAAIAAgGGAAID/gaca9IAAgP2AAICjgACABwAAAAAAAAAAgACAkoAAgP+AAIB+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACA6YAAgP+AAIDxgACAT4AAgAKAAIACgACAUYAAgPOAAIDJgACAHgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAgDKAAID/gACA/4AAgNmAAIDYgACA2IAAgN2AAID/gACAbwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgACAvoAAgO+AAIDvgACA74AAgO+AAIDvgACAw4AAgA4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAQAJAAEAPQABAD0AAQA9AAEAPQABAD0AAQA8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//8AAP//AAAABwAAgAcAAJ/PAADPjwAAz58AAOc/AADjOQAA8nkAAPhzAAD48wAA/AcAAPwHAAD//wAA//8AAA==")

def frame(lines="", COLOR="NOCOLOR"):
  linelist = []
  if not isinstance(lines, list):
    lines = str(lines).split('\n')
  max_len = max(len(re.sub(r'\033\[\d+m', '', str(sline))) for sline in lines) if lines else 0
  frame_width = max_len + 2
  print(cc[COLOR] + '┌' + '─' * frame_width + '┐' + cc[COLOR])
  for sline in lines:
    stripped_len = len(re.sub(r'\033\[\d+m', '', str(sline)))
    padding = ' ' * (max_len - stripped_len)
    print(f"│ {cc['NOCOLOR']}{sline}{padding}{cc[COLOR]} │")
  print(cc[COLOR] + '└' + '─' * frame_width + '┘' + cc["RESET"])

def start():
  message = [
    '      \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m Hello! My name is \033[33m' + __MyName__ + ' \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==',
    f'        Started run : \033[93m {datetime.datetime.fromtimestamp(start_time).strftime("%Y_%m_%d %H:%M:%S")}'
  ]
  frame(message, 'BLUE')

def finish():
  finish_time = time.time()
  message = [
    '      \033[34m==\033[35m==\033[91m==\033[93m==\033[92m==\033[96m== \033[39m My name is \033[33m' + __MyName__ + '\033[39m goodbye. \033[96m==\033[92m==\033[93m==\033[91m==\033[35m==\033[34m==',
    '   Started run  : \033[93m ' + datetime.datetime.fromtimestamp(start_time).strftime('%Y_%m_%d %H:%M:%S'),
    '   Finished run : \033[93m ' + datetime.datetime.fromtimestamp(finish_time).strftime('%Y_%m_%d %H:%M:%S'),
    '   Elapsed time : \033[93m ' + str(datetime.timedelta(seconds=int(finish_time - start_time)))
  ]
  frame(message, 'ORANGE')

def get_computer_name():
  try:
    return subprocess.check_output(["hostname"], text=True).strip()
  except (subprocess.CalledProcessError, FileNotFoundError):
    return platform.node()

def msg(message, **kwargs):
  frame(str(message))
  return f'Message processed: {message}'

def _format_response(id, value, status="Success", error=None):
  response = {"id": id, "status": status, "value": value}
  if error:
    response["value"] = None
    response["error"] = str(error)
  return response

def run_local_function(scope, func_name, params, kwargs):
  try:
    target_func = scope.get(func_name)
    if not target_func:
      raise ValueError(f"Function '{func_name}' not found")
    return target_func(*params, **kwargs)
  except Exception as e:
    return {"error": f"Execution of '{func_name}' failed: {e}"}

class Node:
  def __init__(self, local_functions):
    self.id = str(uuid.uuid4())
    self.local_functions = local_functions
    self.identity = {
      "id": self.id, "myname": __MyName__, "version": "24.1-Lite",
      "type": "passive_sync", "started": start_time,
      "hostname": get_computer_name(), "platform": platform.system(),
      "capabilities": list(self.local_functions.keys()),
      "addresses": [], "abut_nodes": {}
    }
    try:
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        self.identity["addresses"].append([ip, default_port])
    except Exception:
      self.identity["addresses"].append(["127.0.0.1", default_port])

def mkhtml(node):
  return f"""
  <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Node: {node.id[:8]}</title><style>body{{font-family:Arial,sans-serif;background-color:#f4f4f4;color:#333;margin:20px}}table{{width:100%;border-collapse:collapse;margin-top:20px}}table,th,td{{border:1px solid #ddd}}th,td{{padding:12px;text-align:left}}th{{background-color:#0066cc;color:white}}</style></head>
  <body><h2>Node ID: <b>{node.id}</b></h2>
  <table>
    <tr><td>Hostname</td><td>{node.identity['hostname']}</td></tr>
    <tr><td>Name</td><td>{node.identity['myname']}</td></tr>
    <tr><td>Capabilities</td><td>{', '.join(node.identity['capabilities'])}</td></tr>
  </table></body></html>
  """

class NodeHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
  def _send_cors_headers(self):
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')

  def do_OPTIONS(self):
    self.send_response(200)
    self._send_cors_headers()
    self.end_headers()

  def log_message(self, format, *args):
    pass

  def do_GET(self):
    if self.path in ("/", "/index.html"):
      self.send_response(200)
      self._send_cors_headers()
      self.send_header("Content-Type", "text/html")
      self.end_headers()
      self.wfile.write(mkhtml(self.server.node).encode('utf-8'))
    elif self.path in ("/status", "/status/"):
      self.send_response(200)
      self._send_cors_headers()
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      response_data = self.server.node.identity.copy()
      response_data["healthy"] = True
      response_data["busy"] = False
      self.wfile.write(json.dumps(response_data).encode('utf-8'))
    elif self.path == "/favicon.ico":
      self.send_response(200)
      self.send_header("Content-Type", "image/x-icon")
      self.end_headers()
      self.wfile.write(favicon_data)
    else:
      self.send_error(404, "Not Found")
      
  def do_POST(self):
    if self.path == "/":
      try:
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        payload = json.loads(post_data)
      except (TypeError, json.JSONDecodeError):
        self.send_error(400, "Invalid JSON"); return

      calls = payload if isinstance(payload, list) else [payload]
      results = []
      for call in calls:
        func_name = call.get("call")
        if not func_name:
          results.append(_format_response(call.get("id"), None, "Failed", "Missing 'call' parameter."))
          continue
        args = call.get("args", [])
        kwargs = call.get("kwargs", {})
        value = run_local_function(self.server.node.local_functions, func_name, args, kwargs)
        is_error = isinstance(value, dict) and "error" in value
        results.append(_format_response(call.get("id", self.server.node.id), value, "Failed" if is_error else "Success", value.get("error") if is_error else None))
      
      final_response = self.server.node.identity.copy()
      final_response["result"] = results
      response_json = json.dumps(final_response, default=str)
      self.send_response(200)
      self._send_cors_headers()
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(response_json.encode('utf-8'))
    else:
      self.send_error(404, "Not Found")

class ThreadingHTTPServer(http.server.ThreadingHTTPServer):
  def __init__(self, server_address, RequestHandlerClass, node_instance):
    super().__init__(server_address, RequestHandlerClass)
    self.node = node_instance

def auto(external_locals=None, ip=default_ip, port=default_port, not4share=None):
  start()
  internal_not_for_share = [
    'frame', 'start', 'finish', 'get_computer_name', 'mkhtml',
    'run_local_function', '_format_response', 'auto', 'Node',
    'NodeHTTPRequestHandler', 'ThreadingHTTPServer'
  ]
  if not4share:
    internal_not_for_share.extend(not4share)

  shareable_functions = {'msg': msg}
  if external_locals:
    shareable_functions.update({
      name: func for name, func in external_locals.items()
      if inspect.isfunction(func) and name not in internal_not_for_share and not name.startswith('_')
    })
  
  global node
  node = Node(shareable_functions)
  
  try:
    server = ThreadingHTTPServer((ip, port), NodeHTTPRequestHandler, node_instance=node)
  except OSError as e:
    if e.errno == 98 or "Address already in use" in str(e):
      error_message = [
        "FATAL ERROR: Address already in use",
        f"The address http://{ip}:{port} is occupied by another process."
      ]
      frame(error_message, "RED")
      finish()
      return
    else:
      raise
  
  frame(f"Listening on: http://{ip}:{port}", "GREEN")
  
  try:
    server.serve_forever()
  except (KeyboardInterrupt, SystemExit):
    print("\nShutting down server...")
    server.shutdown()
    server.server_close()
    
  finish()

if __name__ == '__main__':
  def multiply(a, b):
    return a * b
  auto(locals())