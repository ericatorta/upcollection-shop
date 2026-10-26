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

    # Spedizione: gratis sopra la soglia, ritiro in negozio sempre gratis
    SOGLIA_SPEDIZIONE_GRATIS = 99
    COSTO_SPEDIZIONE = 7

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
