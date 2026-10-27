"""
Email al cliente a ogni cambio di stato dell'ordine.

Senza SMTP_HOST nel .env non parte niente: il cliente vede comunque lo stato in "I miei ordini".
"""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


def _euro(valore):
    return ("{:,.2f}".format(valore or 0)).replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def istruzioni_pagamento(ordine):
    """Come pagare un ordine con bonifico o Satispay (usato anche nella pagina dell'ordine)."""
    c = current_app.config
    importo = _euro(ordine["totale"])
    causale = "Ordine " + str(ordine["id_ordini"])
    if ordine["pagamento"] == "Bonifico":
        return ("Fai un bonifico di " + importo + " a " + c["INTESTATARIO"]
                + ", IBAN " + (c["IBAN"] or "(te lo scriviamo a parte)")
                + ", causale “" + causale + "”.")
    if ordine["pagamento"] == "Satispay":
        return ("Apri Satispay, cerca “" + c["SATISPAY_NOME"] + "” tra i negozi e paga "
                + importo + " scrivendo nel messaggio “" + causale + "”.")
    return ""


def _testo(ordine):
    numero = "#" + str(ordine["id_ordini"])
    nome = ordine["destinatario"].split(" ")[0]
    stato = ordine["stato"]
    if stato == "da confermare":
        corpo = ("abbiamo ricevuto il tuo ordine " + numero + " (" + _euro(ordine["totale"]) + "). "
                 "Controlliamo che sia tutto disponibile e te lo confermiamo al più presto, "
                 "di solito in giornata.")
    elif stato == "in attesa di pagamento":
        corpo = ("il tuo ordine " + numero + " è confermato e i capi sono messi da parte per te. "
                 + istruzioni_pagamento(ordine) + " Appena riceviamo il pagamento lo prepariamo.")
    elif stato == "confermato":
        corpo = "il tuo ordine " + numero + " è confermato: lo stiamo preparando."
    elif stato == "pronto per il ritiro":
        corpo = ("il tuo ordine " + numero + " ti aspetta in negozio, in "
                 + current_app.config["NEGOZIO"]["indirizzo"] + ".")
    elif stato == "spedito":
        corpo = ("il tuo ordine " + numero + " è partito: arriva a " + ordine["indirizzo"] + ", "
                 + ordine["citta"] + " in 2-4 giorni lavorativi.")
    elif stato == "annullato":
        corpo = ("purtroppo non possiamo evadere il tuo ordine " + numero + ". "
                 "Se avevi già pagato ti rimborsiamo per intero. Per qualsiasi domanda rispondi a questa email.")
    else:
        return None
    return "Ciao " + nome + ",\n\n" + corpo + "\n\nDettagli: " + current_app.config["SITO_URL"] \
        + "/ordine/" + str(ordine["id_ordini"]) + "\n\nGrazie,\nUp Collection · " \
        + current_app.config["NEGOZIO"]["telefono"]


def avvisa_cliente(ordine, righe):
    c = current_app.config
    testo = _testo(ordine)
    if not c["SMTP_HOST"] or not testo:
        return
    messaggio = EmailMessage()
    messaggio["Subject"] = "Ordine #" + str(ordine["id_ordini"]) + " · " + ordine["stato"]
    messaggio["From"] = c["EMAIL_MITTENTE"]
    messaggio["To"] = ordine["email"]
    messaggio["Reply-To"] = c["NEGOZIO"]["email"]
    messaggio.set_content(testo)
    try:
        with smtplib.SMTP(c["SMTP_HOST"], c["SMTP_PORT"], timeout=10) as server:
            server.starttls()
            server.login(c["SMTP_UTENTE"], c["SMTP_PASSWORD"])
            server.send_message(messaggio)
    except Exception as errore:
        log.warning("Email per l'ordine %s non partita: %s", ordine["id_ordini"], errore)
