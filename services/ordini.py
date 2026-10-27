"""
Vita di un ordine: stati, metodi di pagamento e passaggi da uno stato all'altro.

    da confermare ──Conferma──> confermato ──> pronto per il ritiro / spedito ──> consegnato
          │            (bonifico, Satispay: prima "in attesa di pagamento" ──Pagato──> confermato)
          └──Rifiuta──> annullato   (i capi tornano disponibili)

Gli stessi passaggi li usano il pannello admin e i pulsanti del bot Telegram.
"""
from models.database import annulla_ordine, leggi_righe_ordine, modifica_stato_ordine, trova_ordine
from services import email, telegram

STATI_ORDINE = [
    "da confermare",
    "in attesa di pagamento",
    "confermato",
    "pronto per il ritiro",
    "spedito",
    "consegnato",
    "annullato",
]

# metodo di pagamento -> per quale consegna vale ("" = tutte) e testo sotto il nome
PAGAMENTI = {
    "Paga in negozio al ritiro": {"consegna": "ritiro", "nota": "Contanti, carta o bancomat quando passi a prenderlo."},
    "Contrassegno": {"consegna": "spedizione", "nota": "Paghi in contanti al corriere quando arriva il pacco."},
    "Bonifico": {"consegna": "", "nota": "Ti mandiamo l'IBAN appena confermiamo l'ordine."},
    "Satispay": {"consegna": "", "nota": "Paghi dall'app Satispay appena confermiamo l'ordine."},
}
PAGA_DOPO = ("Bonifico", "Satispay")  # si prepara il pacco solo a pagamento ricevuto

# azione -> (stato di partenza ammessi, stato di arrivo, etichetta del pulsante)
AZIONI = {
    "conferma": (["da confermare"], None, "✅ Conferma"),
    "rifiuta": (["da confermare", "in attesa di pagamento", "confermato"], "annullato", "❌ Rifiuta"),
    "pagato": (["in attesa di pagamento"], "confermato", "💶 Pagamento ricevuto"),
    "pronto": (["confermato"], "pronto per il ritiro", "🛍 Pronto per il ritiro"),
    "spedito": (["confermato"], "spedito", "📦 Spedito"),
    "consegnato": (["pronto per il ritiro", "spedito"], "consegnato", "🏁 Consegnato"),
}


def pagamenti_validi(consegna):
    return [nome for nome, info in PAGAMENTI.items() if info["consegna"] in ("", consegna)]


def azioni_possibili(ordine):
    """Le azioni che hanno senso adesso per questo ordine (i pulsanti da mostrare)."""
    azioni = []
    for nome, (da, _, _) in AZIONI.items():
        if ordine["stato"] not in da:
            continue
        if nome == "pronto" and ordine["consegna"] != "ritiro":
            continue
        if nome == "spedito" and ordine["consegna"] == "ritiro":
            continue
        # a ordine confermato "Rifiuta" diventa un annullamento: lo si fa dal pannello, non dal telefono
        if nome == "rifiuta" and ordine["stato"] == "confermato":
            continue
        azioni.append(nome)
    return azioni


def esegui(id_ordine, azione):
    """Applica un'azione all'ordine. Ritorna l'ordine aggiornato, o None se non è possibile."""
    ordine = trova_ordine(id_ordine)
    if not ordine or azione not in azioni_possibili(ordine):
        return None
    nuovo = AZIONI[azione][1]
    if azione == "conferma":
        nuovo = "in attesa di pagamento" if ordine["pagamento"] in PAGA_DOPO else "confermato"
    if nuovo == "annullato":
        annulla_ordine(id_ordine)  # rimette i capi in magazzino
    else:
        modifica_stato_ordine(id_ordine, nuovo)
    ordine = trova_ordine(id_ordine)
    email.avvisa_cliente(ordine, leggi_righe_ordine(id_ordine))
    return ordine


def cambia_stato(id_ordine, stato):
    """Dal pannello admin si può scegliere qualsiasi stato (per correggere errori)."""
    ordine = trova_ordine(id_ordine)
    if not ordine or stato not in STATI_ORDINE or stato == ordine["stato"]:
        return None
    if stato == "annullato":
        annulla_ordine(id_ordine)
    else:
        modifica_stato_ordine(id_ordine, stato)
    ordine = trova_ordine(id_ordine)
    email.avvisa_cliente(ordine, leggi_righe_ordine(id_ordine))
    return ordine


def nuovo_ordine(id_ordine):
    """Appena creato: messaggio Telegram al negozio con i pulsanti Conferma / Rifiuta."""
    ordine = trova_ordine(id_ordine)
    righe = leggi_righe_ordine(id_ordine)
    telegram.invia_ordine(ordine, righe, azioni_possibili(ordine))
    email.avvisa_cliente(ordine, righe)
