import platform, subprocess, re

cc = {
  "RESET": "\033[0m", "NOCOLOR": "\033[39m", "BLACK": "\033[30m", "DRED": "\033[31m", "DGREEN": "\033[32m",
  "ORANGE": "\033[33m", "BLUE": "\033[34m", "VIOLET": "\033[35m", "CYAN": "\033[36m", "LGRAY": "\033[37m",
  "DGRAY": "\033[90m", "RED": "\033[91m", "GREEN": "\033[92m", "YELLOW": "\033[93m", "DBLUE": "\033[94m",
  "PINK": "\033[95m", "LBLUE": "\033[96m", "WHITE": "\033[97m"
}

def _split(s, maxlen=90):
  words = []
  for w in s.split():
    if len(re.sub(r"\033\[\d+m", "", w)) >= maxlen:
      ml = maxlen - 2
      words += [w[i:i+ml] for i in range(0, len(w), ml)]
    else:
      words.append(w)
  lines = []; cur = ""
  for w in words:
    if len(re.sub(r"\033\[\d+m", "", cur)) + len(re.sub(r"\033\[\d+m", "", w)) <= maxlen:
      cur += w + " "
    else:
      lines.append(cur.strip()); cur = w + " "
  if cur: lines.append(cur.strip())
  return lines

def frame(lines="", COLOR="NOCOLOR", frames=25, framemax=92, display=True):
  lst = lines if isinstance(lines, list) else [str(lines)]
  lll = frames - 2
  flat = []
  for s in lst:
    ll = len(re.sub(r"\033\[\d+m", "", str(s)))
    if ll + 2 > framemax:
      for ss in _split(str(s), framemax - 2):
        lll = max(len(re.sub(r"\033\[\d+m", "", ss)), lll); flat.append(ss)
    else:
      lll = max(ll, lll); flat.append(str(s))
  w = lll + 2
  out = [cc[COLOR] + "┌" + "─" * w + "┐" + cc[COLOR]]
  for s in flat:
    pad = " " * (w - len(re.sub(r"\033\[\d+m", "", s)) - 2)
    out.append(f"{cc[COLOR]}│ {cc['NOCOLOR']}{s}{pad}{cc[COLOR]} │")
  out.append(cc[COLOR] + "└" + "─" * w + "┘" + cc["RESET"])
  if display: print("\n".join(out))
  return "\n".join(out)

notif = None
try:
  if platform.system() == "Linux":
    try:
      import notify2; notify2.init("zignode")
      def _notif_linux(message, title="zignode"):
        try: notify2.Notification(title, str(message)).show(); return True
        except: return False
      notif = _notif_linux
    except ImportError:
      try:
        subprocess.run(["which", "notify-send"], check=True, capture_output=True)
        def _notif_send(message, title="zignode"):
          try: subprocess.run(["notify-send", title, str(message), "--expire-time=15000"], check=True); return True
          except: return False
        notif = _notif_send
      except subprocess.CalledProcessError:
        pass
  elif platform.system() == "Darwin":
    def _notif_mac(message, title="zignode"):
      try: subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], check=True); return True
      except: return False
    notif = _notif_mac
  elif platform.system() == "Windows":
    import plyer
    def _notif_win(message, title="zignode"):
      try: plyer.notification.notify(title=title, message=str(message), timeout=15); return True
      except: return False
    notif = _notif_win
except Exception:
  pass

speak = None
try:
  if platform.system() == "Linux":
    if subprocess.run(["which", "RHVoice-test"], capture_output=True).returncode == 0:
      def _speak_rh(message, language="english", rate=2.5, volume=80):
        voice = {"polish": "Alicja", "english": "lyubov"}.get(language.lower())
        if not voice: return False
        try: subprocess.run(["RHVoice-test", "-p", voice, "-v", str(volume), "-r", str(int(rate*60))], input=str(message), text=True, check=True); return True
        except: return False
      speak = _speak_rh
    elif subprocess.run(["which", "espeak"], capture_output=True).returncode == 0:
      def _speak_es(message, language="english", rate=2.5, volume=80):
        try: subprocess.run(["espeak", "-v", {"polish":"pl","english":"en"}.get(language.lower(),"en"), "-s", str(int(rate*100)), "-a", str(int(volume*2)), str(message)], check=True); return True
        except: return False
      speak = _speak_es
  elif platform.system() == "Darwin":
    def _speak_mac(message, language="english", rate=2.5, volume=80):
      voice = {"english": "Alex", "polish": "Zosia"}.get(language.lower(), "Alex")
      try: subprocess.run(["say", "-v", voice, "-r", str(int(rate*100)), str(message)], check=True); return True
      except: return False
    speak = _speak_mac
  elif platform.system() == "Windows":
    import win32com.client, pythoncom
    def _speak_win(message, language="english", rate=2.5, volume=80):
      try:
        pythoncom.CoInitialize()
        s = win32com.client.Dispatch("SAPI.SpVoice"); s.Rate = int(max(-10,min(10,rate))); s.Volume = int(max(0,min(100,volume))); s.Speak(str(message)); return True
      except: return False
      finally:
        try: pythoncom.CoUninitialize()
        except: pass
    speak = _speak_win
except Exception:
  pass

def msg(message, language="english"):
  frame(str(message))
  if speak:
    try: speak(message, language=language)
    except Exception as e: print(f"speak failed: {e}")
  if notif:
    try: notif(message)
    except Exception as e: print(f"notif failed: {e}")
  return f"Message processed: {message}"
