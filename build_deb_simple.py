#!/usr/bin/env python3
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

def run_cmd(cmd, cwd=None, **kwargs):
    env = os.environ.copy()
    env['TMPDIR'] = '/tmp/dpkg-build'
    os.makedirs(env['TMPDIR'], exist_ok=True)
    result = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True, **kwargs)
    return result

def main():
    project_root = Path(__file__).resolve().parent

    with tempfile.TemporaryDirectory(dir="/tmp", prefix="stiky-notes-build-") as tmpdir:
        pkgdir = Path(tmpdir) / "stiky-notes_0.3.2-1_all"

        dirs = [
            pkgdir / "DEBIAN",
            pkgdir / "usr/bin",
            pkgdir / "usr/lib/python3/dist-packages",
            pkgdir / "usr/share/applications",
            pkgdir / "etc/xdg/autostart",
            pkgdir / "usr/share/dbus-1/services",
        ]
        # Tutte le dimensioni icone disponibili
        for size in (16, 22, 24, 32, 48, 64, 128, 256):
            dirs.append(pkgdir / f"usr/share/icons/hicolor/{size}x{size}/apps")
        dirs.append(pkgdir / "usr/share/icons/hicolor/scalable/apps")
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Copy source code directly instead of using wheel
        src_dir = project_root / "src" / "kde_plasma_stiky_notes"
        dst_dir = pkgdir / "usr/lib/python3/dist-packages" / "kde_plasma_stiky_notes"
        shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns("__pycache__"))

        # Installa tutte le icone disponibili
        for size in (16, 22, 24, 32, 48, 64, 128, 256):
            icon_src = project_root / "debian" / "icons" / f"stiky-notes-{size}.png"
            if icon_src.exists():
                shutil.copy(icon_src, pkgdir / f"usr/share/icons/hicolor/{size}x{size}/apps/stiky-notes.png")

        # Icona scalabile (SVG)
        shutil.copy(src_dir / "icons" / "stiky-notes.svg",
                    pkgdir / "usr/share/icons/hicolor/scalable/apps/stiky-notes.svg")

        wrapper = pkgdir / "usr/bin/stiky-notes"
        wrapper.write_text("""#!/bin/sh
export PYTHONPATH="/usr/lib/python3/dist-packages:${PYTHONPATH}"
exec python3 -m kde_plasma_stiky_notes "$@"
""")
        wrapper.chmod(0o755)

        shutil.copy(project_root / "debian" / "stiky-notes.desktop",
                    pkgdir / "usr/share/applications/")
        shutil.copy(project_root / "debian" / "stiky-notes.autostart",
                    pkgdir / "etc/xdg/autostart/stiky-notes.desktop")
        shutil.copy(project_root / "debian" / "org.kde.StikyNotes.service",
                    pkgdir / "usr/share/dbus-1/services/")

        # Normalizza i permessi secondo la policy Debian:
        # directory 755, file 644, script 755
        pkgdir.chmod(0o755)
        for p in sorted(pkgdir.rglob("*"), reverse=True):
            if p.is_dir():
                p.chmod(0o755)
            elif p == wrapper:
                p.chmod(0o755)
            else:
                p.chmod(0o644)
        
        (pkgdir / "DEBIAN" / "control").write_text("""Package: stiky-notes
Version: 0.3.2-1
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pyqt6, python3-pyqt6.qtqml, python3-pyqt6.qtquick, qml6-module-qtquick, qml6-module-qtquick-window, qt6-qpa-plugins
Recommends: kde-plasma-desktop
Maintainer: Stiky-notes Developers <dev@stiky-notes.example.com>
Description: Sticky notes application for KDE Plasma
 Stiky-notes puts sticky notes (post-it) on the KDE Plasma desktop.
 .
 Each note is a small frameless window on the desktop, in the spirit of the
 classic post-it: move it, resize it, give it a colour and a title, keep it
 above other windows. Text, position and size are saved automatically and
 restored at the next login.
 .
 Features:
  * One window per note, 12 colours, optional "always on top"
  * Rich text: bold, italic, underline, strikethrough, bulleted and numbered lists
  * Reminders with a desktop notification
  * Per-note virtual desktop, or all desktops (via KWin)
  * Notes reopen where you left them (via XWayland on Wayland sessions)
  * System tray icon with the list of notes, show/hide all, new note
  * Single instance controlled over D-Bus (org.kde.StikyNotes)
  * Optional autostart on login
""")
        
        postinst = pkgdir / "DEBIAN" / "postinst"
        postinst.write_text("""#!/bin/sh
set -e
update-desktop-database -q /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
exit 0
""")
        postinst.chmod(0o755)
        
        postrm = pkgdir / "DEBIAN" / "postrm"
        postrm.write_text("""#!/bin/sh
set -e
update-desktop-database -q /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
exit 0
""")
        postrm.chmod(0o755)
        
        os.chdir(tmpdir)
        result = run_cmd(f"dpkg-deb --build --root-owner-group stiky-notes_0.3.2-1_all")
        
        if result.returncode == 0:
            generated = Path(tmpdir) / "stiky-notes_0.3.2-1_all.deb"
            output_deb = project_root / "stiky-notes_0.3.2-1_all.deb"
            if generated.exists():
                shutil.move(str(generated), str(output_deb))
                print(f"✓ Package created: {output_deb}")
                print(f"  Size: {output_deb.stat().st_size / 1024 / 1024:.1f} MB")
                return 0
            else:
                print(f"✗ .deb not found at {generated}")
                return 1
        else:
            print(f"✗ Build failed: {result.stderr}")
            return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
