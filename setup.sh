#!/bin/bash
# zignode setup — installs to /opt/zignode, enables systemd service
# Usage: sudo bash setup.sh
set -euo pipefail

ZIGNODE_DIR=/opt/zignode
if [ -t 1 ]; then C='\033[0;36m'; G='\033[0;32m'; Y='\033[0;33m'; N='\033[0m'; else C=''; G=''; Y=''; N=''; fi
info() { echo -e "${C}[zignode] $*${N}"; }
ok()   { echo -e "${G}  ✓ $*${N}"; }
warn() { echo -e "${Y}  ! $*${N}"; }

OS=$(uname -s); ARCH=$(uname -m)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "Setup — $OS $ARCH"

# ── Install files ──────────────────────────────────────────────────────────────
mkdir -p "$ZIGNODE_DIR/libs"
cp -r "$SCRIPT_DIR/libs/"*  "$ZIGNODE_DIR/libs/"
cp    "$SCRIPT_DIR/zignode.config" "$ZIGNODE_DIR/" 2>/dev/null || true
cp    "$SCRIPT_DIR/zignode_monitor.html" "$ZIGNODE_DIR/" 2>/dev/null || true
# Preserve existing config if present
[ ! -f "$ZIGNODE_DIR/zignode.config" ] && \
    cp "$SCRIPT_DIR/zignode.config" "$ZIGNODE_DIR/zignode.config"
ok "Files installed to $ZIGNODE_DIR"

# ── Dependencies ───────────────────────────────────────────────────────────────
if [ "$OS" = "Linux" ]; then
    if command -v pacman &>/dev/null; then
        pacman -S --needed --noconfirm python python-aiohttp python-netifaces2 python-pynacl 2>/dev/null || \
        pacman -S --needed --noconfirm python python-aiohttp python-netifaces  python-pynacl 2>/dev/null || true
        ok "Arch deps installed"
    elif command -v apt-get &>/dev/null; then
        apt-get install -y python3 python3-aiohttp python3-nacl 2>/dev/null || \
        (apt-get install -y python3 python3-pip && pip3 install aiohttp pynacl netifaces)
        ok "Ubuntu deps installed"
    fi
fi

# ── Systemd service ────────────────────────────────────────────────────────────
if command -v systemctl &>/dev/null; then
    if [ -f "$SCRIPT_DIR/zignode.service" ]; then
        install -Dm644 "$SCRIPT_DIR/zignode.service" /usr/lib/systemd/system/zignode.service
        systemctl daemon-reload
        systemctl enable --now zignode
        ok "zignode.service enabled and started"
    fi
fi

ok "zignode installed."
