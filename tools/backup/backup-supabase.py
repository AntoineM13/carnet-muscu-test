#!/usr/bin/env python3
"""
SAUVEGARDE NOCTURNE de la base Supabase de Carnet de muscu (sur le Mac mini).

Copie TOUTES les lignes des tables `docs` (données de chaque compte) et `bank`
(catalogue partagé) dans ~/Sauvegardes/carnet-muscu/carnet-muscu-AAAA-MM-JJ.json,
et garde les 30 derniers fichiers.

La clé SECRÈTE Supabase n'est jamais dans le dépôt : elle est lue dans le
Trousseau macOS (service « carnet-muscu-supabase », compte « backup »).
Rangement (une fois, dans Terminal) :
    security add-generic-password -s carnet-muscu-supabase -a backup -w
Pour les tests : variables CM_BACKUP_KEY et CM_SUPABASE_URL.

Python 3 du Mac, sans rien installer. Lancé chaque nuit par launchd (voir install.sh).
"""
import datetime
import glob
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

SUPABASE_URL = os.environ.get("CM_SUPABASE_URL", "https://axtepwhxhqxrijpkdqfr.supabase.co")
OUT_DIR = os.path.expanduser(os.environ.get("CM_BACKUP_DIR", "~/Sauvegardes/carnet-muscu"))
KEEP = 30
PAGE = 1000
TABLES = {
    # table : (colonnes, ordre stable pour la pagination)
    "docs": ("user_id,collection,id,data,deleted,updated_at", "user_id.asc,collection.asc,id.asc"),
    "bank": ("id,data,created_by,updated_at", "id.asc"),
}


def log(msg):
    print(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def secret_key():
    if os.environ.get("CM_BACKUP_KEY"):
        return os.environ["CM_BACKUP_KEY"]
    try:
        out = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", "carnet-muscu-supabase", "-a", "backup", "-w"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except subprocess.CalledProcessError:
        log("ERREUR : clé introuvable dans le Trousseau (service carnet-muscu-supabase).")
        sys.exit(2)


def fetch_table(table, key):
    cols, order = TABLES[table]
    rows, offset = [], 0
    while True:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={cols}&order={order}&limit={PAGE}&offset={offset}"
        req = urllib.request.Request(url, headers={"apikey": key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as res:
            page = json.load(res)
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def main():
    key = secret_key()
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        data = {t: fetch_table(t, key) for t in TABLES}
    except urllib.error.HTTPError as e:
        log(f"ERREUR HTTP {e.code} : {e.read().decode(errors='replace')[:300]}")
        sys.exit(1)
    except Exception as e:  # réseau, projet en pause…
        log(f"ERREUR : {e}")
        sys.exit(1)

    users = sorted({r["user_id"] for r in data["docs"]})
    sessions = sum(1 for r in data["docs"] if r["collection"] == "sessions" and not r["deleted"])
    backup = {
        "format": "carnet-muscu/supabase-backup", "version": 1,
        "exportedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "counts": {"docs": len(data["docs"]), "bank": len(data["bank"]), "users": len(users), "sessions": sessions},
        **data,
    }
    name = f"carnet-muscu-{datetime.date.today():%Y-%m-%d}.json"
    path = os.path.join(OUT_DIR, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False)
    os.replace(tmp, path)  # jamais de fichier à moitié écrit

    files = sorted(glob.glob(os.path.join(OUT_DIR, "carnet-muscu-*.json")))
    for old in files[:-KEEP]:
        os.remove(old)
    log(f"OK {name} : {len(users)} comptes, {sessions} séances, {len(data['docs'])} lignes, "
        f"{len(data['bank'])} exercices partagés ({os.path.getsize(path) // 1024} Ko). "
        f"{min(len(files), KEEP)} sauvegardes conservées.")


if __name__ == "__main__":
    main()
