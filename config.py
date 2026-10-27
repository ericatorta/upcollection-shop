"""Configurazione centralizzata: chiave segreta, database, Groq e dati del negozio."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cartella principale del progetto
BASE_DIR = Path(__file__).resolve().parent

# Carica SECRET_KEY e GROQ_API_KEY dal file .env (che non va su GitHub)
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "cambiami-in-produzione")

    # Il file database.db viene creato nella cartella models
    DATABASE = os.path.join(os.path.dirname(__file__), "models/database.db")

    # Facoltativa: serve solo alla stylist IA
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    # i modelli di Groq cambiano: se questo sparisce, mettine un altro in .env
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Indirizzo pubblico del sito (serve per i link nelle email e su Telegram)
    SITO_URL = os.getenv("SITO_URL", "http://localhost:5065").rstrip("/")

    # Password dell'admin creata al primo avvio. In produzione va messa nel .env:
    # senza, il sito crea gli account di prova (admin/Admin123! e cliente/Cliente123!)
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    # Spedizione: gratis sopra la soglia, ritiro in negozio sempre gratis
    SOGLIA_SPEDIZIONE_GRATIS = 99
    COSTO_SPEDIZIONE = 7
    # supplemento del corriere per il pagamento alla consegna
    COSTO_CONTRASSEGNO = float(os.getenv("COSTO_CONTRASSEGNO", "0"))

    # Pagamenti dopo la conferma: dati per bonifico e Satispay
    IBAN = os.getenv("IBAN", "")
    INTESTATARIO = os.getenv("INTESTATARIO", "Up Collection di Torta Federico e C. s.a.s.")
    SATISPAY_NOME = os.getenv("SATISPAY_NOME", "Up Collection")
    # Satispay compare al checkout solo quando il negozio ha Satispay Business attivo
    SATISPAY_ATTIVO = os.getenv("SATISPAY_ATTIVO", "") == "1"

    # Telegram: il bot avvisa di ogni ordine con i pulsanti Conferma / Rifiuta
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    # parte segreta dell'indirizzo del webhook: solo Telegram la conosce
    TELEGRAM_SEGRETO = os.getenv("TELEGRAM_SEGRETO", "")

    # Email ai clienti (conferma, pagamento, spedizione). Facoltative: senza, non parte nessuna email
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_UTENTE = os.getenv("SMTP_UTENTE", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_MITTENTE = os.getenv("EMAIL_MITTENTE", "Up Collection <info@upcollectiontorino.com>")

    # Dati obbligatori del venditore (footer, condizioni di vendita)
    DATI_LEGALI = {
        "ragione_sociale": "Up Collection di Torta Federico e C. s.a.s.",
        "sede": "Corso Racconigi 159/D, 10141 Torino (TO)",
        "piva": "04924200019",
        "rea": "TO-670774",
    }

    # Loghi dei marchi nella fascia che scorre in home: file in static/img/marchi
    # e "scala" (stessa superficie per tutti: i loghi lunghi più bassi, quelli quadrati più alti)
    LOGHI_MARCHI = {
        "Armani Exchange": ("armani-exchange.svg", 0.92),
        "Blauer": ("blauer.png", 0.56),
        "Bomboogie": ("bomboogie.png", 0.55),
        "Gallo": ("gallo.svg", 0.66),
        "Happy Socks": ("happy-socks.svg", 0.29),
        "Jeckerson": ("jeckerson.svg", 0.34),
        "Liu Jo": ("liu-jo.svg", 0.54),
        "North Sails": ("north-sails.svg", 0.92),
        "Roy Roger's": ("roy-rogers.svg", 0.31),
        "Sun68": ("sun68.svg", 0.73),
        "Take Two": ("take-two.png", 0.55),
    }

    NEGOZIO = {
        "nome": "Up Collection",
        "indirizzo": "Corso Racconigi 159D, 10141 Torino",
        "telefono": "011 331867",
        "whatsapp": "39011331867",
        "email": "info@upcollectiontorino.com",
        "instagram": "https://www.instagram.com/upcollection.torino/",
        "facebook": "https://www.facebook.com/p/Up-Collection-Abbigliamento-Torino-100046418003879/",
        "tiktok": "https://www.tiktok.com/@upcollection.torino",
        "mappa": "https://maps.app.goo.gl/FM2YBDB1PjBqrfrq5",
        "orari": [
            ("Lunedì", "15:30 – 19:30"),
            ("Martedì – Sabato", "9:30 – 12:30 · 15:30 – 19:30"),
            ("Domenica", "Chiuso"),
        ],
    }
