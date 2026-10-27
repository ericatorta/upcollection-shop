"""Copia di sicurezza del database, da lanciare ogni notte (cron sul server).

    python3 strumenti/backup_db.py /srv/upcollection-shop-backup

Usa la copia "a caldo" di SQLite: il sito può restare acceso mentre copia.
Tiene gli ultimi 30 backup e cancella i più vecchi.
"""
import glob
import os
import sqlite3
import sys
from datetime import datetime

CARTELLA_SITO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(CARTELLA_SITO, "models", "database.db")
DA_TENERE = 30

destinazione = sys.argv[1] if len(sys.argv) > 1 else os.path.join(CARTELLA_SITO, "backup")
os.makedirs(destinazione, exist_ok=True)

file_backup = os.path.join(destinazione, "database-" + datetime.now().strftime("%Y%m%d-%H%M") + ".db")
origine = sqlite3.connect("file:" + DATABASE + "?mode=ro", uri=True)
copia = sqlite3.connect(file_backup)
try:
    origine.backup(copia)
finally:
    copia.close()
    origine.close()

# controllo che la copia si apra e sia sana
controllo = sqlite3.connect(file_backup)
esito = controllo.execute("PRAGMA integrity_check").fetchone()[0]
controllo.close()
if esito != "ok":
    sys.exit("Backup rovinato: " + file_backup)

for vecchio in sorted(glob.glob(os.path.join(destinazione, "database-*.db")))[:-DA_TENERE]:
    os.remove(vecchio)
print("Backup ok:", file_backup)
