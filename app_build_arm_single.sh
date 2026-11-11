#!/bin/bash
set -euo pipefail

# --- KONFIGURATION ---
APP_NAME="DJ Gadget AI-Suite Pro v3.3.1 @bagueDEV ARM"
ICON_FILE="icon.icns"
VERSION="3.3.1"
DEST_APP="dist/$APP_NAME.app"

# Farben
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== START SINGLE-BINARY BUILD (ARM / M1-M4 OPTIMIZED) ===${NC}"

# Python / PyInstaller Ermittlung (WICHTIG: python3.11, da alle Pakete dort installiert sind)
PY_CMD="python3"
if [ -f "./venv/bin/python3.11" ]; then
    PY_CMD="./venv/bin/python3.11"
    echo -e "${GREEN}🐍 Verwende Virtual Environment: $PY_CMD${NC}"
elif [ -f "./venv/bin/python3" ]; then
    PY_CMD="./venv/bin/python3"
    echo -e "${GREEN}🐍 Verwende Virtual Environment: $PY_CMD${NC}"
fi

# 1. Aufräumen
echo -e "${GREEN}🧹 Lösche alte Build-Ordner...${NC}"
rm -rf build dist *.spec

# 2. Der zentrale PyInstaller-Aufruf
# Wir bauen EINE App. Die Worker (analyzer/separator/transcriber/chatbot) werden
# als Module mit eingepackt und von main.py als Dispatcher via `--worker <type>`
# aufgerufen (get_worker_cmd -> [sys.executable ... --worker <type>]).
# --collect-all sorgt dafür, dass alle KI-Modelle und Binaries (Metal/C++) dabei sind.
echo -e "${GREEN}🔨 Baue Single-Binary-App...${NC}"
"$PY_CMD" -m PyInstaller --noconfirm --distpath dist --workpath build --log-level WARN \
    --onedir --windowed \
    --name="$APP_NAME" \
    --icon="$ICON_FILE" \
    --add-data "tabs:tabs" \
    --add-data "helpers.py:." \
    --add-data "analyzer.py:." \
    --add-data "separator.py:." \
    --add-data "transcriber.py:." \
    --add-data "chatbot.py:." \
    --add-data "melody_generator.py:." \
    --add-data "samples:samples" \
    --add-data "llama_server_bin:llama_cpp_server" \
    --add-data "LICENSE:." \
    --add-data "THIRD_PARTY_LICENSES.md:." \
    --collect-all "demucs" \
    --collect-all "demucs_mlx" \
    --collect-all "mlx" \
    --collect-all "safetensors" \
    --collect-all "faster_whisper" \
    --collect-all "numpy" \
    --collect-all "certifi" \
    --exclude-module "torch" \
    --exclude-module "torchaudio" \
    --hidden-import "demucs_mlx.api" \
    --hidden-import "pandas" \
    --hidden-import "analyzer" \
    --hidden-import "separator" \
    --hidden-import "transcriber" \
    --hidden-import "chatbot" \
    main.py

if [ ! -d "$DEST_APP" ]; then
    echo -e "${RED}❌ Fehler: App-Bundle $DEST_APP wurde nicht gefunden.${NC}"
    exit 1
fi

# 3. Info.plist Versionierung & macOS Tweaks
PLIST_PATH="$DEST_APP/Contents/Info.plist"

if [ -f "$PLIST_PATH" ]; then
    echo "📝 Setze Version $VERSION in Info.plist..."
    /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST_PATH" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$PLIST_PATH"

    /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST_PATH" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$PLIST_PATH"

    /usr/libexec/PlistBuddy -c "Set :NSHighResolutionCapable true" "$PLIST_PATH" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :NSHighResolutionCapable bool true" "$PLIST_PATH"
fi

# 4. Rechte & Ad-Hoc-Signatur (WICHTIG für macOS ARM / Apple Silicon)
echo -e "${GREEN}🔑 Setze Ausführrechte, entferne Quarantäne & signiere ad-hoc...${NC}"

chmod +x "$DEST_APP/Contents/MacOS/$APP_NAME"

# Quarantäne entfernen (mit Fallback, falls symbolische Links im Bundle liegen)
xattr -cr "$DEST_APP" 2>/dev/null || true

codesign --force --deep --sign - "$DEST_APP"

# 5. DMG Erstellung für einfachen Transport / Release
echo -e "${GREEN}📦 Erstelle DMG für einfachen Transport...${NC}"
DMG_PATH="dist/${APP_NAME}.dmg"
rm -f "$DMG_PATH"

mkdir -p dist/dmg_root
cp -R "$DEST_APP" dist/dmg_root/
# Lizenztexte gehören zum Download (GPLv3 + Lizenzen der verwendeten Bibliotheken)
cp LICENSE dist/dmg_root/LICENSE.txt
cp THIRD_PARTY_LICENSES.md dist/dmg_root/THIRD_PARTY_LICENSES.md
ln -s /Applications dist/dmg_root/Applications
hdiutil create -volname "$APP_NAME" -srcfolder dist/dmg_root -ov -format UDZO "$DMG_PATH"
rm -rf dist/dmg_root

echo -e "${GREEN}✅ FERTIG! BUILD ERFOLGREICH BEENDET!${NC}"
echo "Deine App liegt hier: $DEST_APP"
echo "Deine DMG-Datei liegt hier: $DMG_PATH"