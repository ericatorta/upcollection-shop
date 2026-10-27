"""
Email al cliente a ogni cambio di stato dell'ordine.

Senza SMTP_HOST nel .env non parte niente: il cliente vede comunque lo stato in "I miei ordini".
"""
import logging
import smtplib
from urllib.parse import quote
from email.message import EmailMessage

from flask import current_app, render_template

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


def _testo(ordine, firma=True):
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
                 "Se avevi già pagato ti rimborsiamo per intero. Per qualsiasi domanda scrivici, ti rispondiamo subito.")
    else:
        return None
    testo = "Ciao " + nome + ",\n\n" + corpo + "\n\nDettagli: " + current_app.config["SITO_URL"] \
        + "/ordine/" + str(ordine["id_ordini"])
    if firma:
        testo += "\n\nGrazie,\nUp Collection · " + current_app.config["NEGOZIO"]["telefono"]
    return testo


def link_whatsapp(ordine):
    """Link che apre WhatsApp sulla chat del cliente con il messaggio dello stato attuale già scritto."""
    numero = "".join(c for c in ordine["telefono"] if c.isdigit())
    if numero.startswith("00"):
        numero = numero[2:]
    if len(numero) <= 10:  # numero italiano senza prefisso (es. 333 1234567 o 011 331867)
        numero = "39" + numero
    testo = _testo(ordine, firma=False)
    if len(numero) < 11 or not testo:
        return ""
    return "https://wa.me/" + numero + "?text=" + quote(testo + "\n\nUp Collection")


# stato -> (oggetto dell'email, titolo grande, occhiello sopra il titolo)
TITOLI = {
    "da confermare": ("Abbiamo ricevuto il tuo ordine #{n}", "Grazie, {nome}.", "Ordine ricevuto"),
    "in attesa di pagamento": ("Ordine #{n} confermato: ecco come pagare", "È tutto disponibile.", "Ordine confermato"),
    "confermato": ("Ordine #{n} confermato", "Lo stiamo preparando.", "Ordine confermato"),
    "pronto per il ritiro": ("Il tuo ordine #{n} ti aspetta in negozio", "Ti aspettiamo.", "Pronto per il ritiro"),
    "spedito": ("Il tuo ordine #{n} è partito", "È in viaggio.", "Ordine spedito"),
    "annullato": ("Ordine #{n} annullato", "Ci dispiace, {nome}.", "Ordine annullato"),
}


def _foto(indirizzo):
    """Le email hanno bisogno di indirizzi completi e delle foto piccole."""
    if indirizzo and indirizzo.startswith("/"):
        indirizzo = current_app.config["SITO_URL"] + indirizzo
    return (indirizzo or "").replace(".jpg", "-s.jpg")


def html_email(ordine, righe):
    """La versione impaginata dell'email (templates/email/ordine.html)."""
    testo = _testo(ordine, firma=False)
    if not testo:
        return None
    nome = ordine["destinatario"].split(" ")[0]
    _, titolo, occhiello = TITOLI[ordine["stato"]]
    # il paragrafo principale è lo stesso del testo semplice, senza saluto e link
    corpo = testo.split("\n\n")[1]
    corpo = corpo[0].upper() + corpo[1:]
    istruzioni = istruzioni_pagamento(ordine) if ordine["stato"] == "in attesa di pagamento" else ""
    if istruzioni:
        corpo = corpo.replace(" " + istruzioni, "")
    return render_template(
        "email/ordine.html",
        ordine=ordine, righe=righe, foto=_foto, euro=_euro,
        titolo=titolo.format(nome=nome), occhiello=occhiello, corpo=corpo, istruzioni=istruzioni,
        sito=current_app.config["SITO_URL"], negozio=current_app.config["NEGOZIO"],
        legali=current_app.config["DATI_LEGALI"],
    )


def avvisa_cliente(ordine, righe):
    c = current_app.config
    testo = _testo(ordine)
    if not c["SMTP_HOST"] or not testo:
        return
    nome = ordine["destinatario"].split(" ")[0]
    messaggio = EmailMessage()
    messaggio["Subject"] = TITOLI[ordine["stato"]][0].format(n=ordine["id_ordini"], nome=nome)
    messaggio["From"] = c["EMAIL_MITTENTE"]
    messaggio["To"] = ordine["email"]
    messaggio["Reply-To"] = c["NEGOZIO"]["email"]
    messaggio.set_content(testo)  # per chi legge le email solo come testo
    messaggio.add_alternative(html_email(ordine, righe), subtype="html")
    try:
        with smtplib.SMTP(c["SMTP_HOST"], c["SMTP_PORT"], timeout=10) as server:
            server.starttls()
            server.login(c["SMTP_UTENTE"], c["SMTP_PASSWORD"])
            server.send_message(messaggio)
    except Exception as errore:
        log.warning("Email per l'ordine %s non partita: %s", ordine["id_ordini"], errore)
