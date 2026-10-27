"""
Carica nel negozio il catalogo della vetrina (assets/data/prodotti.json di upcollectiontorino.com).

    python strumenti/importa_vetrina.py percorso/prodotti.json

Sostituisce TUTTI i prodotti: si usa solo prima dell'apertura (con zero ordini, altrimenti si ferma).
Regole decise da Erica il 27/10/2026:
  - taglie a lettere: donna S, M, L · uomo M, L, XL (calze, cappelli "U" e borse restano come sono)
  - un pezzo per capo; calze e confezioni Happy Socks con i pezzi contati in negozio
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models.database import db_connection

FOTO = "https://upcollectiontorino.com/"
# foto non ancora pubblicate sulla vetrina: le serve il negozio stesso
FOTO_LOCALI = {"lj-abito-scuba"}

TIPI = {
    "maglieria": "Maglieria", "felpe": "Felpe", "pantaloni": "Pantaloni", "abiti": "Abiti",
    "capispalla": "Capispalla", "tshirt": "T-shirt", "borse": "Borse", "cappelli": "Cappelli",
    "calze": "Calze", "regali": "Idee regalo",
}

TAGLIE = {"donna": "S,M,L", "uomo": "M,L,XL"}

# pezzi in negozio (Happy Socks contate il 9/10/2026)
PEZZI = {
    "hs-calze-camping": 4, "hs-calze-righe-blocchi": 3, "hs-calze-righe-ondulate": 3,
    "hs-calze-righe-verticali": 3, "hs-calze-snoopy-righe": 3, "hs-calze-snoopy-righe-donna": 2,
    "hs-calze-star-wars-stormtrooper": 6, "hs-calze-star-wars-yoda": 6, "hs-calze-gatti": 6,
    "hs-calze-argyle": 6, "hs-calze-tulipani": 6, "hs-calze-orsi": 3, "hs-calze-fiori-verticali": 2,
    "hs-calze-peanuts-in-crowd": 3, "hs-calze-cani": 6, "hs-calze-peanuts-garden-chill": 6,
    "hs-calze-plus": 3, "hs-calze-sneaker-lupo": 6, "hs-calze-puppy-love": 3,
    "hs-regalo-gingerbread": 2, "hs-regalo-santa": 3, "hs-regalo-santa-donna": 3,
    "hs-regalo-hot-chocolate": 2, "hs-regalo-beer": 2, "hs-box-peanuts-3": 2, "hs-box-wine-2": 2,
    "hs-box-merry-cracker-2": 2, "hs-box-lucky-neko-2": 2, "hs-box-holiday-heart-2": 1,
}


def riga(p):
    lettere = any(t in ("S", "M", "L", "XL") for t in p["sizes"])
    taglie = TAGLIE[p["cat"]] if lettere else ",".join(p["sizes"])
    if p["id"] in FOTO_LOCALI:
        immagini = ["/static/img/prodotti/" + f.split("assets/img/prodotti/")[1] for f in p["images"]]
    else:
        immagini = [FOTO + f for f in p["images"]]
    return (
        p["name"]["it"], p["brand"], p["cat"], TIPI[p["type"]], p["color"]["it"],
        "\n".join(p.get("bullets", {}).get("it", [])), float(p["price"]), taglie,
        ",".join(immagini), PEZZI.get(p["id"], 1), 1 if p.get("isNew") else 0,
    )


def main(percorso):
    prodotti = json.load(open(percorso, encoding="utf-8"))["prodotti"]
    righe = [riga(p) for p in prodotti]
    with app.app_context(), db_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM ordini").fetchone()[0]:
            sys.exit("Ci sono già ordini: non sostituisco il catalogo.")
        conn.execute("DELETE FROM prodotti")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'prodotti'")
        conn.executemany("""
            INSERT INTO prodotti
                (nome, marca, categoria, tipo, colore, descrizione,
                 prezzo, taglie, immagini, quantita, novita)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, righe)
    senza_conteggio = [p["id"] for p in prodotti if p["type"] in ("calze", "regali") and p["id"] not in PEZZI]
    print(len(righe), "prodotti caricati")
    print("calze senza pezzi contati (messo 1):", ", ".join(senza_conteggio))


if __name__ == "__main__":
    main(sys.argv[1])
