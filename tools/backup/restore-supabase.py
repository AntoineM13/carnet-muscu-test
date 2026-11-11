#!/usr/bin/env python3
"""
RESTAURATION d'une sauvegarde nocturne dans Supabase (à n'utiliser qu'en cas
de problème, avec Claude ou en suivant docs/DEPLOIEMENT.md §5).

    python3 restore-supabase.py ~/Sauvegardes/carnet-muscu/carnet-muscu-AAAA-MM-JJ.json
        → affiche le contenu (comptes, séances), ne modifie RIEN.
    python3 restore-supabase.py FICHIER --user <id du compte> --apply
        → réinjecte les lignes de CE compte (recommandé : un compte à la fois).
    python3 restore-supabase.py FICHIER --all --apply
        → réinjecte tous les comptes.
    Ajouter --bank pour réinjecter aussi le catalogue partagé.

Les lignes sont réécrites telles qu'elles étaient dans la sauvegarde : une
modification faite APRÈS la sauvegarde sur ces mêmes lignes serait remplacée.
Les téléphones reçoivent la version restaurée à leur prochaine synchro.
Même clé que la sauvegarde (Trousseau, service « carnet-muscu-supabase »).
"""
import argparse
import collections
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402

backup = import_module("backup-supabase")
BATCH = 500


def post(path, rows, key, on_conflict):
    for i in range(0, len(rows), BATCH):
        body = json.dumps(rows[i:i + BATCH]).encode()
        req = urllib.request.Request(
            f"{backup.SUPABASE_URL}/rest/v1/{path}?on_conflict={on_conflict}", data=body, method="POST",
            headers={"apikey": key, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        urllib.request.urlopen(req, timeout=60).read()


def main():
    ap = argparse.ArgumentParser(description="Restaurer une sauvegarde Carnet de muscu dans Supabase")
    ap.add_argument("file")
    ap.add_argument("--user", help="id du compte à restaurer (voir la liste affichée)")
    ap.add_argument("--all", action="store_true", help="tous les comptes")
    ap.add_argument("--bank", action="store_true", help="restaurer aussi le catalogue partagé")
    ap.add_argument("--apply", action="store_true", help="écrire vraiment (sinon : simple aperçu)")
    a = ap.parse_args()

    with open(os.path.expanduser(a.file), encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format") != "carnet-muscu/supabase-backup":
        sys.exit("Ce fichier n'est pas une sauvegarde nocturne Carnet de muscu.")

    per_user = collections.defaultdict(collections.Counter)
    for r in data["docs"]:
        if not r["deleted"]:
            per_user[r["user_id"]][r["collection"]] += 1
    print(f"Sauvegarde du {data['exportedAt'][:16].replace('T', ' ')} (UTC)")
    for uid, c in per_user.items():
        print(f"  compte {uid} : {c['sessions']} séances, {c['exercises']} exercices, {c['templates']} séances modèles")
    print(f"  catalogue partagé : {len(data['bank'])} exercices")

    if not a.apply:
        print("\nAperçu seulement : rien n'a été modifié. Ajouter --user <id> --apply (ou --all --apply).")
        return
    if not a.user and not a.all:
        sys.exit("Préciser --user <id> ou --all.")
    rows = [r for r in data["docs"] if a.all or r["user_id"] == a.user]
    if not rows:
        sys.exit("Aucune ligne pour ce compte dans la sauvegarde.")
    if input(f"\nRéécrire {len(rows)} lignes dans Supabase ? Taper RESTAURER pour confirmer : ").strip() != "RESTAURER":
        sys.exit("Annulé.")
    key = backup.secret_key()
    post("docs", [{k: r[k] for k in ("user_id", "collection", "id", "data", "deleted")} for r in rows], key, "user_id,collection,id")
    if a.bank and data["bank"]:
        post("bank", [{k: r[k] for k in ("id", "data", "created_by")} for r in data["bank"]], key, "id")
    print("Restauration terminée. Les téléphones récupèrent les données à leur prochaine synchronisation.")


if __name__ == "__main__":
    main()
