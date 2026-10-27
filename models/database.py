"""
MODEL: tutto quello che parla con il database.

Il controller non scrive SQL: chiama queste funzioni e usa quello che restituiscono.

Tabelle
    utenti         clienti registrati e amministratori (ruolo 'cliente' o 'admin')
    prodotti       il catalogo (immagini = indirizzi separati da virgola)
    ordini         chi ha comprato, dove spedire, stato e totale
    righe_ordine   i capi dentro ogni ordine (nome e prezzo copiati al momento
                   dell'acquisto, così l'ordine resta giusto anche se il prodotto cambia)
    messaggi       quello che arriva dal modulo "Contatti"
"""
import sqlite3
from contextlib import contextmanager
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from models.prodotti_demo import PRODOTTI_DEMO

DATABASE = Config.DATABASE


def connessione():
    """Apre il database.
    - row_factory: posso leggere le colonne per nome, es. prodotto["prezzo"]
    - foreign_keys ON: senza, SQLite ignora FOREIGN KEY e ON DELETE
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection():
    """Apre, conferma se va tutto bene, annulla se c'è un errore, chiude sempre."""
    conn = connessione()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crea_database():
    """Crea le tabelle e, solo la prima volta, gli account e il catalogo di esempio."""
    with db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                id_utenti INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                nome TEXT NOT NULL,
                cognome TEXT NOT NULL,
                email TEXT NOT NULL,
                ruolo TEXT NOT NULL DEFAULT 'cliente'
                    CHECK(ruolo IN ('cliente', 'admin'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prodotti (
                id_prodotti INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                marca TEXT NOT NULL,
                categoria TEXT NOT NULL CHECK(categoria IN ('donna', 'uomo')),
                tipo TEXT NOT NULL,
                colore TEXT NOT NULL DEFAULT '',
                descrizione TEXT NOT NULL DEFAULT '',
                prezzo REAL NOT NULL CHECK(prezzo >= 0),
                taglie TEXT NOT NULL DEFAULT '',
                immagini TEXT NOT NULL DEFAULT '',
                quantita INTEGER NOT NULL DEFAULT 0 CHECK(quantita >= 0),
                novita INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ordini (
                id_ordini INTEGER PRIMARY KEY AUTOINCREMENT,
                id_utenti INTEGER NOT NULL,
                data TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                stato TEXT NOT NULL DEFAULT 'da confermare',
                destinatario TEXT NOT NULL,
                telefono TEXT NOT NULL,
                consegna TEXT NOT NULL,
                indirizzo TEXT,
                cap TEXT,
                citta TEXT,
                pagamento TEXT NOT NULL,
                note TEXT,
                spedizione REAL NOT NULL DEFAULT 0,
                totale REAL NOT NULL,
                FOREIGN KEY (id_utenti) REFERENCES utenti(id_utenti) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS righe_ordine (
                id_righe INTEGER PRIMARY KEY AUTOINCREMENT,
                id_ordini INTEGER NOT NULL,
                id_prodotti INTEGER,
                nome TEXT NOT NULL,
                marca TEXT NOT NULL,
                immagine TEXT,
                taglia TEXT,
                quantita INTEGER NOT NULL CHECK(quantita > 0),
                prezzo REAL NOT NULL CHECK(prezzo >= 0),
                FOREIGN KEY (id_ordini) REFERENCES ordini(id_ordini) ON DELETE CASCADE,
                FOREIGN KEY (id_prodotti) REFERENCES prodotti(id_prodotti) ON DELETE SET NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messaggi (
                id_messaggi INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                oggetto TEXT,
                messaggio TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # aggiunta il 27/10/2026: data di registrazione dei clienti (i database già esistenti non l'avevano)
        colonne = [c["name"] for c in conn.execute("PRAGMA table_info(utenti)")]
        if "registrato" not in colonne:
            conn.execute("ALTER TABLE utenti ADD COLUMN registrato TEXT")

        # i numeri d'ordine partono da 1000 (deciso il 27/10/2026): AUTOINCREMENT continua da qui
        conn.execute("""
            INSERT INTO sqlite_sequence (name, seq)
            SELECT 'ordini', 999
            WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = 'ordini')
        """)
        conn.execute("""
            UPDATE sqlite_sequence SET seq = 999 WHERE name = 'ordini' AND seq < 999
        """)

        # primo avvio online: solo l'admin, con la password scelta nel .env
        if conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0] == 0 and Config.ADMIN_PASSWORD:
            conn.execute("""
                INSERT INTO utenti (username, password, nome, cognome, email, ruolo)
                VALUES ('admin', ?, 'Federico', 'Torta', 'info@upcollectiontorino.com', 'admin')
            """, (generate_password_hash(Config.ADMIN_PASSWORD),))
        # primo avvio in locale: account di prova
        if conn.execute("SELECT COUNT(*) FROM utenti").fetchone()[0] == 0:
            conn.executemany("""
                INSERT INTO utenti (username, password, nome, cognome, email, ruolo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                ("admin", generate_password_hash("Admin123!"),
                 "Federico", "Torta", "info@upcollectiontorino.com", "admin"),
                ("cliente", generate_password_hash("Cliente123!"),
                 "Giulia", "Rossi", "giulia@example.com", "cliente"),
            ])

        # primo avvio: catalogo di esempio
        if conn.execute("SELECT COUNT(*) FROM prodotti").fetchone()[0] == 0:
            conn.executemany("""
                INSERT INTO prodotti
                    (nome, marca, categoria, tipo, colore, descrizione,
                     prezzo, taglie, immagini, quantita, novita)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, PRODOTTI_DEMO)


# UTENTI

def registra_utente(username, password, nome, cognome, email):
    """Nuovo cliente. La password viene salvata solo come hash."""
    with db_connection() as conn:
        conn.execute("""
            INSERT INTO utenti (username, password, nome, cognome, email, ruolo, registrato)
            VALUES (?, ?, ?, ?, ?, 'cliente', datetime('now', 'localtime'))
        """, (username, generate_password_hash(password), nome, cognome, email))


def leggi_clienti(cerca=""):
    """Clienti registrati (admin) con numero di ordini e speso, i più recenti per primi."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT utenti.id_utenti, utenti.username, utenti.nome, utenti.cognome,
                   utenti.email, utenti.registrato,
                   COUNT(ordini.id_ordini) AS ordini,
                   COALESCE(SUM(CASE WHEN ordini.stato != 'annullato' THEN ordini.totale END), 0) AS speso,
                   MAX(ordini.telefono) AS telefono
            FROM utenti
            LEFT JOIN ordini ON ordini.id_utenti = utenti.id_utenti
            WHERE utenti.ruolo = 'cliente'
              AND (? = '' OR utenti.nome || ' ' || utenti.cognome || ' ' || utenti.email || ' ' || utenti.username LIKE ?)
            GROUP BY utenti.id_utenti
            ORDER BY utenti.id_utenti DESC
        """, (cerca, "%" + cerca + "%")).fetchall()


def login_utente(username, password):
    """Restituisce l'utente se username e password sono giusti, altrimenti None."""
    with db_connection() as conn:
        utente = conn.execute("""
            SELECT * FROM utenti WHERE username = ?
        """, (username,)).fetchone()
    if utente and check_password_hash(utente["password"], password):
        return utente
    return None


def trova_utente(id):
    """Un utente per id (senza password)."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT id_utenti, username, nome, cognome, email, ruolo
            FROM utenti
            WHERE id_utenti = ?
        """, (id,)).fetchone()


def modifica_utente(id, nome, cognome, email):
    """Aggiorna i dati del profilo."""
    with db_connection() as conn:
        conn.execute("""
            UPDATE utenti
            SET nome = ?, cognome = ?, email = ?
            WHERE id_utenti = ?
        """, (nome, cognome, email, id))


# PRODOTTI (vetrina)

def leggi_prodotti(categoria="", tipo="", marca="", ricerca="", solo_novita=0, ordina=""):
    """Catalogo con filtri.
    Ogni filtro vuoto viene ignorato grazie a (? = '' OR colonna = ?):
    così la query è sempre la stessa e i valori passano solo come parametri.
    """
    parola = "%" + ricerca + "%"
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE (? = '' OR categoria = ?)
            AND (? = '' OR tipo = ?)
            AND (? = '' OR marca = ?)
            AND (? = '' OR nome LIKE ? OR marca LIKE ? OR tipo LIKE ? OR colore LIKE ?)
            AND (? = 0 OR novita = 1)
            ORDER BY
                CASE WHEN ? = 'prezzo-crescente' THEN prezzo END ASC,
                CASE WHEN ? = 'prezzo-decrescente' THEN prezzo END DESC,
                novita DESC,
                id_prodotti DESC
        """, (
            categoria, categoria,
            tipo, tipo,
            marca, marca,
            ricerca, parola, parola, parola, parola,
            solo_novita,
            ordina, ordina
        )).fetchall()


def leggi_novita(limite=8):
    """Gli ultimi arrivi per la home."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE novita = 1 AND quantita > 0
            ORDER BY id_prodotti DESC
            LIMIT ?
        """, (limite,)).fetchall()


def leggi_selezione(limite=8):
    """Un mix a caso per "Scelti per te"."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE quantita > 0
            ORDER BY RANDOM()
            LIMIT ?
        """, (limite,)).fetchall()


def trova_prodotto(id):
    """Un prodotto per id (None se non esiste)."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti WHERE id_prodotti = ?
        """, (id,)).fetchone()


def prodotti_simili(prodotto, limite=4):
    """Stessa categoria, prima quelli dello stesso tipo, poi della stessa marca."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE categoria = ? AND id_prodotti != ? AND quantita > 0
            ORDER BY (tipo = ?) DESC, (marca = ?) DESC, RANDOM()
            LIMIT ?
        """, (prodotto["categoria"], prodotto["id_prodotti"],
              prodotto["tipo"], prodotto["marca"], limite)).fetchall()


def leggi_tipi(categoria=""):
    """Tipi di capo con quanti prodotti ci sono (per i filtri)."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT tipo, COUNT(*) AS totale
            FROM prodotti
            WHERE (? = '' OR categoria = ?)
            GROUP BY tipo
            ORDER BY tipo
        """, (categoria, categoria)).fetchall()


def leggi_marche(categoria=""):
    """Marche presenti, con quanti prodotti."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT marca, COUNT(*) AS totale
            FROM prodotti
            WHERE (? = '' OR categoria = ?)
            GROUP BY marca
            ORDER BY marca
        """, (categoria, categoria)).fetchall()


def cerca_per_stylist(categoria="", tipi=None, marca="", prezzo_max=0, limite=4):
    """Capi disponibili che rispettano i criteri capiti dalla domanda.
    tipi è una lista (es. ["Capispalla"]); lista vuota = qualsiasi tipo.
    prezzo_max 0 = nessun limite di prezzo.
    """
    tipi = tipi or []
    # tanti "?" quanti sono i tipi: i valori passano sempre come parametri
    segnaposti = ", ".join("?" for t in tipi) or "''"
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE quantita > 0
            AND (? = '' OR categoria = ?)
            AND (? = 0 OR tipo IN (""" + segnaposti + """))
            AND (? = '' OR marca = ?)
            AND (? = 0 OR prezzo <= ?)
            ORDER BY novita DESC, RANDOM()
            LIMIT ?
        """, [categoria, categoria, len(tipi)] + tipi
             + [marca, marca, prezzo_max, prezzo_max, limite]).fetchall()


def trova_prodotti(ids):
    """Più prodotti per id, nell'ordine in cui li ho chiesti."""
    trovati = [trova_prodotto(id) for id in ids]
    return [p for p in trovati if p]


# PRODOTTI (pannello admin)

def inserisci_prodotto(nome, marca, categoria, tipo, colore, descrizione,
                       prezzo, taglie, immagini, quantita, novita):
    with db_connection() as conn:
        conn.execute("""
            INSERT INTO prodotti
                (nome, marca, categoria, tipo, colore, descrizione,
                 prezzo, taglie, immagini, quantita, novita)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, marca, categoria, tipo, colore, descrizione,
              prezzo, taglie, immagini, quantita, novita))


def modifica_prodotto(id, nome, marca, categoria, tipo, colore, descrizione,
                      prezzo, taglie, immagini, quantita, novita):
    with db_connection() as conn:
        conn.execute("""
            UPDATE prodotti
            SET nome = ?, marca = ?, categoria = ?, tipo = ?, colore = ?,
                descrizione = ?, prezzo = ?, taglie = ?, immagini = ?,
                quantita = ?, novita = ?
            WHERE id_prodotti = ?
        """, (nome, marca, categoria, tipo, colore, descrizione,
              prezzo, taglie, immagini, quantita, novita, id))


def elimina_prodotto(id):
    """Gli ordini già fatti restano: nelle righe id_prodotti diventa NULL."""
    with db_connection() as conn:
        conn.execute("DELETE FROM prodotti WHERE id_prodotti = ?", (id,))


def scorte_basse(soglia=2):
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM prodotti
            WHERE quantita <= ?
            ORDER BY quantita, nome
        """, (soglia,)).fetchall()


# ORDINI

def crea_ordine(id_utenti, destinatario, telefono, consegna, indirizzo, cap,
                citta, pagamento, note, spedizione, righe):
    """Salva ordine + righe e scala le quantità, tutto in UNA transazione.
    righe = lista di dizionari {id, taglia, quantita}.
    Se un capo non basta più, ValueError: db_connection annulla tutto.
    """
    with db_connection() as conn:
        controllate, subtotale = [], 0
        for riga in righe:
            prodotto = conn.execute("""
                SELECT * FROM prodotti WHERE id_prodotti = ?
            """, (riga["id"],)).fetchone()
            if not prodotto or prodotto["quantita"] < riga["quantita"]:
                raise ValueError("Quantità non disponibile")
            controllate.append((prodotto, riga))
            subtotale += prodotto["prezzo"] * riga["quantita"]

        id_ordine = conn.execute("""
            INSERT INTO ordini
                (id_utenti, destinatario, telefono, consegna, indirizzo, cap,
                 citta, pagamento, note, spedizione, totale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_utenti, destinatario, telefono, consegna, indirizzo, cap,
              citta, pagamento, note, spedizione, subtotale + spedizione)).lastrowid

        for prodotto, riga in controllate:
            conn.execute("""
                INSERT INTO righe_ordine
                    (id_ordini, id_prodotti, nome, marca, immagine, taglia, quantita, prezzo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (id_ordine, prodotto["id_prodotti"], prodotto["nome"], prodotto["marca"],
                  prodotto["immagini"].split(",")[0], riga["taglia"],
                  riga["quantita"], prodotto["prezzo"]))
            conn.execute("""
                UPDATE prodotti SET quantita = quantita - ? WHERE id_prodotti = ?
            """, (riga["quantita"], prodotto["id_prodotti"]))
    return id_ordine


def leggi_ordini_utente(id_utenti):
    """Ordini di un cliente, con quanti capi contiene ognuno."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT ordini.*, SUM(righe_ordine.quantita) AS capi
            FROM ordini
            JOIN righe_ordine ON righe_ordine.id_ordini = ordini.id_ordini
            WHERE ordini.id_utenti = ?
            GROUP BY ordini.id_ordini
            ORDER BY ordini.id_ordini DESC
        """, (id_utenti,)).fetchall()


def leggi_ordini(stato=""):
    """Tutti gli ordini (admin), con nome del cliente."""
    with db_connection() as conn:
        return conn.execute("""
            SELECT ordini.*, utenti.username, SUM(righe_ordine.quantita) AS capi
            FROM ordini
            JOIN utenti ON utenti.id_utenti = ordini.id_utenti
            JOIN righe_ordine ON righe_ordine.id_ordini = ordini.id_ordini
            WHERE (? = '' OR ordini.stato = ?)
            GROUP BY ordini.id_ordini
            ORDER BY ordini.id_ordini DESC
        """, (stato, stato)).fetchall()


def trova_ordine(id):
    with db_connection() as conn:
        return conn.execute("""
            SELECT ordini.*, utenti.username, utenti.email
            FROM ordini
            JOIN utenti ON utenti.id_utenti = ordini.id_utenti
            WHERE ordini.id_ordini = ?
        """, (id,)).fetchone()


def leggi_righe_ordine(id_ordini):
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM righe_ordine WHERE id_ordini = ? ORDER BY id_righe
        """, (id_ordini,)).fetchall()


def annulla_ordine(id):
    """Ordine annullato: i capi tornano disponibili, tutto in una transazione."""
    with db_connection() as conn:
        stato = conn.execute("""
            SELECT stato FROM ordini WHERE id_ordini = ?
        """, (id,)).fetchone()
        if not stato or stato["stato"] == "annullato":
            return
        conn.execute("""
            UPDATE prodotti
            SET quantita = quantita + (
                SELECT SUM(righe_ordine.quantita) FROM righe_ordine
                WHERE righe_ordine.id_ordini = ? AND righe_ordine.id_prodotti = prodotti.id_prodotti
            )
            WHERE id_prodotti IN (
                SELECT id_prodotti FROM righe_ordine WHERE id_ordini = ?
            )
        """, (id, id))
        conn.execute("""
            UPDATE ordini SET stato = 'annullato' WHERE id_ordini = ?
        """, (id,))


def modifica_stato_ordine(id, stato):
    with db_connection() as conn:
        conn.execute("""
            UPDATE ordini SET stato = ? WHERE id_ordini = ?
        """, (stato, id))


def statistiche():
    """Numeri per la dashboard dell'admin."""
    with db_connection() as conn:
        return {
            "ordini": conn.execute("SELECT COUNT(*) FROM ordini").fetchone()[0],
            "incasso": conn.execute("""
                SELECT COALESCE(SUM(totale), 0) FROM ordini WHERE stato != 'annullato'
            """).fetchone()[0],
            "da_preparare": conn.execute("""
                SELECT COUNT(*) FROM ordini WHERE stato = 'da confermare'
            """).fetchone()[0],
            "clienti": conn.execute("""
                SELECT COUNT(*) FROM utenti WHERE ruolo = 'cliente'
            """).fetchone()[0],
            "prodotti": conn.execute("SELECT COUNT(*) FROM prodotti").fetchone()[0],
            "messaggi": conn.execute("SELECT COUNT(*) FROM messaggi").fetchone()[0],
        }


# MESSAGGI

def inserisci_messaggio(nome, email, oggetto, messaggio):
    with db_connection() as conn:
        conn.execute("""
            INSERT INTO messaggi (nome, email, oggetto, messaggio)
            VALUES (?, ?, ?, ?)
        """, (nome, email, oggetto, messaggio))


def leggi_messaggi():
    with db_connection() as conn:
        return conn.execute("""
            SELECT * FROM messaggi ORDER BY id_messaggi DESC
        """).fetchall()


def elimina_messaggio(id):
    with db_connection() as conn:
        conn.execute("DELETE FROM messaggi WHERE id_messaggi = ?", (id,))
