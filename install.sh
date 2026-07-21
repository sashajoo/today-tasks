#!/bin/bash
# Today Tasks — installer. Builds the .app bundle and installs the `today` CLI.
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Today Tasks.app"
PY="${PYTHON:-/usr/bin/python3}"

echo "Today Tasks installer"
echo "  python: $PY ($($PY --version 2>&1))"

# --- dependencies ---------------------------------------------------------
if ! $PY -c "import AppKit, WebKit, Quartz" >/dev/null 2>&1; then
  echo "  installing PyObjC (no admin password needed)…"
  $PY -m pip install --user --quiet \
    pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz
  $PY -c "import AppKit, WebKit, Quartz" || {
    echo "PyObjC install failed. Try: $PY -m pip install --user pyobjc" >&2
    exit 1
  }
fi
echo "  dependencies ok"

# --- app bundle -----------------------------------------------------------
pkill -f "Today Tasks.app/Contents/Resources/main.py" 2>/dev/null || true
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$HERE/src/main.py" "$HERE/src/index.html" "$APP/Contents/Resources/"

cat > "$APP/Contents/MacOS/TodayTasks" <<EOF
#!/bin/bash
DIR="\$(cd "\$(dirname "\$0")/../Resources" && pwd)"
exec $PY "\$DIR/main.py" >> "\$HOME/Library/Logs/TodayTasks.log" 2>&1
EOF
chmod +x "$APP/Contents/MacOS/TodayTasks"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Today Tasks</string>
  <key>CFBundleDisplayName</key><string>Today Tasks</string>
  <key>CFBundleIdentifier</key><string>com.sashazhu.todaytasks</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleExecutable</key><string>TodayTasks</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF
echo "  installed: $APP"

# --- CLI ------------------------------------------------------------------
BIN=""
for d in /opt/homebrew/bin /usr/local/bin; do
  if [ -d "$d" ] && [ -w "$d" ]; then BIN="$d"; break; fi
done
BIN="${BIN:-$HOME/.local/bin}"
mkdir -p "$BIN"
cp "$HERE/bin/today" "$BIN/today"
chmod +x "$BIN/today"
echo "  installed: $BIN/today"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "  NOTE: $BIN is not on your PATH — add it in ~/.zshrc to use \`today\`" ;;
esac

# --- launch ---------------------------------------------------------------
open "$APP"
sleep 2
if pgrep -f "Today Tasks.app/Contents/Resources/main.py" >/dev/null; then
  echo
  echo "Running. Look at the right side of your desktop."
  echo "Show the desktop (four-finger spread or F11) if your apps are covering it."
  echo "Tip: add it to System Settings > General > Login Items to start at login."
else
  echo "Failed to start — see ~/Library/Logs/TodayTasks.log" >&2
  exit 1
fi
