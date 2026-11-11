#!/bin/bash
# Installe la sauvegarde nocturne sur le Mac mini (à relancer après une
# modification de backup-supabase.py). Rien à installer : Python 3 du Mac.
#  - copie le script hors de ~/Documents (dossier protégé par macOS : une tâche
#    planifiée ne peut pas y lire) dans ~/Library/Application Support/carnet-muscu ;
#  - crée la tâche launchd « fr.carnetmuscu.backup » : tous les jours à 3 h
#    (si le Mac dort, elle tourne à son réveil) ;
#  - journal : ~/Sauvegardes/carnet-muscu/backup.log
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/carnet-muscu"
OUT="$HOME/Sauvegardes/carnet-muscu"
PLIST="$HOME/Library/LaunchAgents/fr.carnetmuscu.backup.plist"
mkdir -p "$APP" "$OUT" "$HOME/Library/LaunchAgents"
cp "$SRC/backup-supabase.py" "$SRC/restore-supabase.py" "$APP/"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>fr.carnetmuscu.backup</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>$APP/backup-supabase.py</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$OUT/backup.log</string>
  <key>StandardErrorPath</key><string>$OUT/backup.log</string>
</dict>
</plist>
PLIST
launchctl bootout "gui/$(id -u)/fr.carnetmuscu.backup" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Sauvegarde nocturne installée (tous les jours à 3 h). Fichiers : $OUT"
