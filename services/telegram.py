"""
Bot Telegram del negozio: avvisa di ogni nuovo ordine e riceve i tocchi sui pulsanti.

Senza TELEGRAM_TOKEN e TELEGRAM_CHAT_ID nel .env non fa niente (il sito funziona lo stesso).
Configurazione: strumenti/telegram_setup.py
"""
import html
import json
import logging
import urllib.request

from flask import current_app

log = logging.getLogger(__name__)


def _chiama(metodo, dati):
    """Chiamata all'API di Telegram. Se qualcosa va storto lo scrive nel log e basta:
    un problema di Telegram non deve mai bloccare un ordine."""
    token = current_app.config["TELEGRAM_TOKEN"]
    if not token:
        return None
    richiesta = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/" + metodo,
        data=json.dumps(dati).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=8) as risposta:
            return json.load(risposta)
    except Exception as errore:
        log.warning("Telegram %s non riuscito: %s", metodo, errore)
        return None


def _euro(valore):
    return ("{:,.2f}".format(valore or 0)).replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def testo_ordine(ordine, righe):
    e = html.escape
    if ordine["consegna"] == "ritiro":
        consegna = "🏬 Ritiro in negozio"
    else:
        consegna = "🚚 " + e(ordine["indirizzo"] + ", " + ordine["cap"] + " " + ordine["citta"])
    capi = "\n".join(
        "• " + e(r["marca"] + " " + r["nome"])
        + (" · taglia " + e(r["taglia"]) if r["taglia"] else "")
        + " × " + str(r["quantita"]) + " — " + _euro(r["prezzo"] * r["quantita"])
        for r in righe
    )
    testo = (
        "<b>🛒 Ordine #" + str(ordine["id_ordini"]) + "</b> · " + _euro(ordine["totale"]) + "\n"
        + "Stato: <b>" + e(ordine["stato"]) + "</b>\n\n"
        + capi + "\n\n"
        + "👤 " + e(ordine["destinatario"]) + " · " + e(ordine["telefono"]) + "\n"
        + "✉️ " + e(ordine["email"]) + "\n"
        + consegna + "\n"
        + "💳 " + e(ordine["pagamento"])
        + (" · spedizione " + _euro(ordine["spedizione"]) if ordine["spedizione"] else "")
    )
    if ordine["note"]:
        testo += "\n📝 " + e(ordine["note"])
    return testo


def _tastiera(ordine, azioni):
    from services.ordini import AZIONI
    from services.email import link_whatsapp
    bottoni = [[{"text": AZIONI[a][2], "callback_data": a + ":" + str(ordine["id_ordini"])}] for a in azioni]
    whatsapp = link_whatsapp(ordine)
    if whatsapp:
        bottoni.append([{"text": "💬 Avvisa su WhatsApp", "url": whatsapp}])
    sito = current_app.config["SITO_URL"]
    if sito.startswith("https://"):  # Telegram accetta solo link pubblici
        bottoni.append([{"text": "Apri nel pannello", "url": sito + "/ordine/" + str(ordine["id_ordini"])}])
    return {"inline_keyboard": bottoni}


def invia_ordine(ordine, righe, azioni):
    chat = current_app.config["TELEGRAM_CHAT_ID"]
    if not chat:
        return
    _chiama("sendMessage", {
        "chat_id": chat,
        "text": testo_ordine(ordine, righe),
        "parse_mode": "HTML",
        "reply_markup": _tastiera(ordine, azioni),
    })


def aggiorna_messaggio(chat_id, id_messaggio, ordine, righe, azioni):
    """Dopo un tocco: stesso messaggio con il nuovo stato e i pulsanti del passo successivo."""
    _chiama("editMessageText", {
        "chat_id": chat_id,
        "message_id": id_messaggio,
        "text": testo_ordine(ordine, righe),
        "parse_mode": "HTML",
        "reply_markup": _tastiera(ordine, azioni),
    })


def rispondi_tocco(id_tocco, testo):
    """Il fumetto che compare in alto su Telegram dopo aver toccato un pulsante."""
    _chiama("answerCallbackQuery", {"callback_query_id": id_tocco, "text": testo})


def scrivi(chat_id, testo):
    _chiama("sendMessage", {"chat_id": chat_id, "text": testo})
