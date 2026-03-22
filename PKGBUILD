# Maintainer: zigfi
pkgname=zignode-git
pkgver=20260316
pkgrel=1
pkgdesc="Distributed node daemon with encrypted WebSocket channels"
arch=('any')
url="ssh://nas3/git/zignode"
license=('MIT')
depends=('python' 'python-aiohttp' 'python-pynacl')
optdepends=('python-netifaces2: network scanning' 'python-netifaces: network scanning (fallback)')
options=(!strip)
backup=('opt/zignode/zignode.config')

source=("git+ssh://nas3/git/zignode")
sha256sums=('SKIP')

pkgver() {
    cd "$srcdir/zignode"
    git log -1 --format='%cd' --date='format:%Y%m%d'
}

package() {
    cd "$srcdir/zignode"

    # Core libs
    install -dm755 "$pkgdir/opt/zignode/libs"
    install -Dm644 libs/zignoded.py    "$pkgdir/opt/zignode/libs/zignoded.py"
    install -Dm644 libs/zignode.py     "$pkgdir/opt/zignode/libs/zignode.py"
    install -Dm644 libs/zignode_lite.py "$pkgdir/opt/zignode/libs/zignode_lite.py"
    install -Dm644 libs/zignode_utils.py "$pkgdir/opt/zignode/libs/zignode_utils.py"
    install -Dm644 libs/__init__.py    "$pkgdir/opt/zignode/libs/__init__.py"

    # Config (backup — pacman preserves .pacsave)
    install -Dm644 zignode.config      "$pkgdir/opt/zignode/zignode.config"

    # Monitor HTML
    install -Dm644 zignode_monitor.html "$pkgdir/opt/zignode/zignode_monitor.html"

    # Systemd service
    install -Dm644 zignode.service     "$pkgdir/usr/lib/systemd/system/zignode.service"
}

post_install() {
    echo ""
    echo ">>> zignode installed to /opt/zignode"
    echo ">>> Enable and start: systemctl enable --now zignode"
    echo ">>> Edit config: /opt/zignode/zignode.config"
    echo ""
}

post_upgrade() {
    systemctl daemon-reload
    systemctl is-active --quiet zignode && systemctl restart zignode || true
}
