"""
Configura il bot Telegram degli ordini.

1. Su Telegram apri @BotFather, scrivi /newbot e copia il token che ti dà.
2. Apri il tuo bot e scrivigli /start (dal telefono che deve ricevere gli ordini).
3. python strumenti/telegram_setup.py TOKEN
       -> mostra il codice della chat (TELEGRAM_CHAT_ID)
4. python strumenti/telegram_setup.py TOKEN https://shop.upcollectiontorino.com SEGRETO
       -> collega il bot al sito: i tocchi su Conferma / Rifiuta arrivano a /telegram/SEGRETO
"""
import json
import sys
import urllib.parse
import urllib.request


def chiama(token, metodo, **dati):
    url = "https://api.telegram.org/bot" + token + "/" + metodo
    corpo = urllib.parse.urlencode(dati).encode() if dati else None
    with urllib.request.urlopen(url, data=corpo, timeout=15) as risposta:
        return json.load(risposta)


if len(sys.argv) == 2:
    token = sys.argv[1]
    chat = {}
    for agg in chiama(token, "getUpdates")["result"]:
        messaggio = agg.get("message") or {}
        if messaggio:
            persona = messaggio["chat"]
            chat[persona["id"]] = persona.get("first_name", "") + " " + persona.get("last_name", "")
    if not chat:
        print("Nessun messaggio: scrivi /start al bot e rilancia.")
    for id_chat, nome in chat.items():
        print("TELEGRAM_CHAT_ID=" + str(id_chat) + "   (" + nome.strip() + ")")
elif len(sys.argv) == 4:
    token, sito, segreto = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
    print(chiama(token, "setWebhook", url=sito + "/telegram/" + segreto,
                 allowed_updates='["message","callback_query"]'))
else:
    print(__doc__)
