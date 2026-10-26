"""
CONTROLLER: tutte le route del negozio (Blueprint "shop").

    vetrina      home, catalogo, scheda prodotto
    carrello     aggiungi, aggiorna, rimuovi, checkout
    account      registrazione, login, profilo, i miei ordini
    contatti     modulo pubblico + stylist IA (Groq)
    admin        dashboard, prodotti (CRUD), ordini, messaggi
"""
from functools import wraps
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from models.database import (
    registra_utente,
    login_utente,
    trova_utente,
    modifica_utente,
    leggi_prodotti,
    leggi_novita,
    leggi_selezione,
    trova_prodotto,
    prodotti_simili,
    leggi_tipi,
    leggi_marche,
    inserisci_prodotto,
    modifica_prodotto,
    elimina_prodotto,
    scorte_basse,
    crea_ordine,
    leggi_ordini_utente,
    leggi_ordini,
    trova_ordine,
    leggi_righe_ordine,
    modifica_stato_ordine,
    statistiche,
    inserisci_messaggio,
    leggi_messaggi,
    elimina_messaggio,
)

shop = Blueprint("shop", __name__)

STATI_ORDINE = ["ricevuto", "in preparazione", "spedito", "pronto per il ritiro", "consegnato", "annullato"]
PAGAMENTI = ["Paga in negozio al ritiro", "Contrassegno", "Carta (simulato)"]


# DECORATOR

def current_user():
    """L'utente che ha fatto l'accesso, riletto dal database (o None)."""
    id_utenti = session.get("id_utenti")
    if not id_utenti:
        return None
    return trova_utente(id_utenti)


def login_required(view):
    """Fa entrare solo chi ha fatto il login; gli altri vanno al login e poi tornano qui."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("id_utenti"):
            flash("Accedi per continuare.", "warning")
            return redirect(url_for("shop.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*ruoli):
    """Come login_required, ma controlla anche il ruolo."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            utente = current_user()
            if utente is None or utente["ruolo"] not in ruoli:
                flash("Non hai i permessi per accedere a questa pagina.", "error")
                return redirect(url_for("shop.index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


# CARRELLO: sta nella sessione come {"id|taglia": quantità}, es. {"12|M": 1, "3|": 2}

def righe_carrello():
    """Trasforma il carrello della sessione in righe complete (prodotto, taglia, totale)."""
    righe, subtotale = [], 0
    for chiave, quantita in session.get("carrello", {}).items():
        id_prodotti, taglia = chiave.split("|")
        prodotto = trova_prodotto(int(id_prodotti))
        if prodotto:
            totale_riga = prodotto["prezzo"] * int(quantita)
            righe.append({
                "chiave": chiave, "prodotto": prodotto, "taglia": taglia,
                "quantita": int(quantita), "totale_riga": totale_riga,
            })
            subtotale += totale_riga
    return righe, subtotale


def pagina_successiva(predefinita):
    """Dopo login/registrazione torno alla pagina di prima, ma solo se è interna al sito."""
    prossima = request.args.get("next", "")
    if prossima.startswith("/") and not prossima.startswith("//"):
        return prossima
    return predefinita


def costo_spedizione(subtotale, consegna):
    """Ritiro in negozio gratis; spedizione gratis sopra la soglia."""
    if consegna == "ritiro" or subtotale >= current_app.config["SOGLIA_SPEDIZIONE_GRATIS"]:
        return 0
    return current_app.config["COSTO_SPEDIZIONE"]


# VETRINA

@shop.route("/")
def index():
    return render_template(
        "index.html",
        novita=leggi_novita(8),
        selezione=leggi_selezione(8),
        marche=leggi_marche(),
    )


@shop.route("/catalogo")
def catalogo():
    """Catalogo con filtri nell'indirizzo: /catalogo?categoria=donna&tipo=Maglieria"""
    categoria = request.args.get("categoria", "").strip()
    tipo = request.args.get("tipo", "").strip()
    marca = request.args.get("marca", "").strip()
    ricerca = request.args.get("q", "").strip()
    ordina = request.args.get("ordina", "").strip()
    solo_novita = request.args.get("novita", default=0, type=int)
    prodotti = leggi_prodotti(categoria, tipo, marca, ricerca, solo_novita, ordina)
    return render_template(
        "catalogo.html",
        prodotti=prodotti,
        tipi=leggi_tipi(categoria),
        marche=leggi_marche(categoria),
        filtri={"categoria": categoria, "tipo": tipo, "marca": marca,
                "q": ricerca, "ordina": ordina, "novita": solo_novita},
    )


@shop.route("/prodotto/<int:id>")
def prodotto(id):
    p = trova_prodotto(id)
    if not p:
        flash("Prodotto non trovato.", "error")
        return redirect(url_for("shop.catalogo"))
    return render_template("prodotto.html", p=p, simili=prodotti_simili(p, 4))


# CARRELLO E CHECKOUT (il carrello si può riempire anche senza account)

@shop.route("/carrello", methods=["GET", "POST"])
def carrello():
    if request.method == "POST":
        id_prodotti = request.form.get("id_prodotti", type=int)
        quantita = request.form.get("quantita", default=1, type=int)
        taglia = request.form.get("taglia", "").strip()
        p = trova_prodotto(id_prodotti) if id_prodotti else None
        if not p or not quantita or quantita < 1:
            flash("Prodotto o quantità non validi.", "error")
            return redirect(url_for("shop.catalogo"))
        if p["taglie"] and taglia not in p["taglie"].split(","):
            flash("Scegli una taglia.", "warning")
            return redirect(url_for("shop.prodotto", id=id_prodotti))
        voci = session.get("carrello", {})
        chiave = str(id_prodotti) + "|" + taglia
        if p["quantita"] < int(voci.get(chiave, 0)) + quantita:
            flash("Ne abbiamo solo " + str(p["quantita"]) + " disponibili.", "error")
            return redirect(url_for("shop.prodotto", id=id_prodotti))
        voci[chiave] = int(voci.get(chiave, 0)) + quantita
        session["carrello"] = voci
        flash(p["nome"] + " è nel carrello.", "success")
        return redirect(url_for("shop.carrello"))

    righe, subtotale = righe_carrello()
    return render_template(
        "carrello.html",
        righe=righe,
        subtotale=subtotale,
        spedizione=costo_spedizione(subtotale, "spedizione"),
    )


@shop.route("/carrello/aggiorna", methods=["POST"])
def aggiorna_carrello():
    """Cambia la quantità di una riga; 0 la toglie."""
    chiave = request.form.get("chiave", "")
    quantita = request.form.get("quantita", default=1, type=int)
    voci = session.get("carrello", {})
    if chiave in voci:
        if quantita and quantita > 0:
            p = trova_prodotto(int(chiave.split("|")[0]))
            if p and quantita > p["quantita"]:
                quantita = p["quantita"]
                flash("Ne abbiamo solo " + str(quantita) + " disponibili.", "warning")
            voci[chiave] = quantita
        else:
            voci.pop(chiave)
        session["carrello"] = voci
    return redirect(url_for("shop.carrello"))


@shop.route("/carrello/rimuovi", methods=["POST"])
def rimuovi_dal_carrello():
    voci = session.get("carrello", {})
    voci.pop(request.form.get("chiave", ""), None)
    session["carrello"] = voci
    flash("Articolo rimosso.", "success")
    return redirect(url_for("shop.carrello"))


@shop.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    utente = current_user()
    righe, subtotale = righe_carrello()
    if not righe:
        flash("Il carrello è vuoto.", "warning")
        return redirect(url_for("shop.catalogo"))

    if request.method == "POST":
        destinatario = request.form.get("destinatario", "").strip()
        telefono = request.form.get("telefono", "").strip()
        consegna = request.form.get("consegna", "spedizione")
        indirizzo = request.form.get("indirizzo", "").strip()
        cap = request.form.get("cap", "").strip()
        citta = request.form.get("citta", "").strip()
        pagamento = request.form.get("pagamento", "")
        note = request.form.get("note", "").strip()
        if not destinatario or not telefono or pagamento not in PAGAMENTI:
            flash("Compila nome, telefono e metodo di pagamento.", "error")
        elif consegna == "spedizione" and (not indirizzo or not cap or not citta):
            flash("Per la spedizione servono indirizzo, CAP e città.", "error")
        else:
            try:
                id_ordine = crea_ordine(
                    utente["id_utenti"], destinatario, telefono, consegna,
                    indirizzo, cap, citta, pagamento, note,
                    costo_spedizione(subtotale, consegna),
                    [{"id": r["prodotto"]["id_prodotti"], "taglia": r["taglia"],
                      "quantita": r["quantita"]} for r in righe],
                )
                session["carrello"] = {}
                return redirect(url_for("shop.grazie", id=id_ordine))
            except ValueError:
                flash("Un capo nel carrello non è più disponibile in quella quantità.", "error")
                return redirect(url_for("shop.carrello"))

    return render_template(
        "checkout.html",
        utente=utente,
        righe=righe,
        subtotale=subtotale,
        spedizione=costo_spedizione(subtotale, "spedizione"),
        pagamenti=PAGAMENTI,
    )


@shop.route("/grazie/<int:id>")
@login_required
def grazie(id):
    ordine = trova_ordine(id)
    if not ordine or ordine["id_utenti"] != session["id_utenti"]:
        return redirect(url_for("shop.ordini"))
    return render_template("grazie.html", ordine=ordine, righe=leggi_righe_ordine(id))


# ACCOUNT

@shop.route("/registrati", methods=["GET", "POST"])
def registrati():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        nome = request.form.get("nome", "").strip()
        cognome = request.form.get("cognome", "").strip()
        email = request.form.get("email", "").strip()
        if len(username) < 3 or len(password) < 6:
            flash("Username minimo 3 caratteri e password minimo 6.", "error")
        elif not nome or not cognome or "@" not in email:
            flash("Nome, cognome ed email sono obbligatori.", "error")
        else:
            try:
                registra_utente(username, password, nome, cognome, email)
                # accesso automatico subito dopo la registrazione
                utente = login_utente(username, password)
                session["id_utenti"] = utente["id_utenti"]
                session["ruolo"] = utente["ruolo"]
                flash("Benvenuta/o in Up Collection, " + nome + "!", "success")
                return redirect(pagina_successiva(url_for("shop.index")))
            except Exception:
                flash("Username già utilizzato.", "error")
    return render_template("registrati.html")


@shop.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        utente = login_utente(username, password)
        if utente:
            # tengo il carrello: lo svuoto solo dopo l'ordine
            carrello = session.get("carrello", {})
            session.clear()
            session["id_utenti"] = utente["id_utenti"]
            session["ruolo"] = utente["ruolo"]
            session["carrello"] = carrello
            flash("Bentornata/o, " + utente["nome"] + ".", "success")
            if utente["ruolo"] == "admin":
                return redirect(pagina_successiva(url_for("shop.admin")))
            return redirect(pagina_successiva(url_for("shop.index")))
        flash("Credenziali non valide.", "error")
    return render_template("login.html")


@shop.route("/logout")
def logout():
    session.clear()
    flash("A presto!", "success")
    return redirect(url_for("shop.index"))


@shop.route("/profilo", methods=["GET", "POST"])
@login_required
def profilo():
    utente = current_user()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cognome = request.form.get("cognome", "").strip()
        email = request.form.get("email", "").strip()
        if not nome or not cognome or "@" not in email:
            flash("Nome, cognome ed email sono obbligatori.", "error")
        else:
            modifica_utente(utente["id_utenti"], nome, cognome, email)
            flash("Profilo aggiornato.", "success")
            return redirect(url_for("shop.profilo"))
    return render_template("profilo.html", utente=utente,
                           ordini=leggi_ordini_utente(utente["id_utenti"]))


@shop.route("/ordini")
@login_required
def ordini():
    return redirect(url_for("shop.profilo") + "#ordini")


@shop.route("/ordine/<int:id>")
@login_required
def scheda_ordine(id):
    """Il cliente vede solo i suoi ordini, l'admin tutti."""
    utente = current_user()
    ordine = trova_ordine(id)
    if not ordine or (utente["ruolo"] != "admin" and ordine["id_utenti"] != utente["id_utenti"]):
        flash("Ordine non trovato.", "error")
        return redirect(url_for("shop.profilo"))
    return render_template("scheda_ordine.html", ordine=ordine,
                           righe=leggi_righe_ordine(id), stati=STATI_ORDINE)


# CONTATTI E STYLIST IA

@shop.route("/contatti", methods=["GET", "POST"])
def contatti():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        oggetto = request.form.get("oggetto", "").strip()
        messaggio = request.form.get("messaggio", "").strip()
        if not nome or "@" not in email or not messaggio:
            flash("Nome, email e messaggio sono obbligatori.", "error")
        else:
            inserisci_messaggio(nome, email, oggetto, messaggio)
            flash("Grazie " + nome + ", ti rispondiamo entro un giorno lavorativo.", "success")
            return redirect(url_for("shop.contatti"))
    return render_template("contatti.html")


@shop.route("/stylist", methods=["GET", "POST"])
def stylist():
    """Visitatori: risposta fissa. Clienti con account: Groq, con il catalogo come contesto."""
    utente, risposta, domanda = current_user(), None, ""
    if request.method == "POST":
        domanda = request.form.get("domanda", "").strip()
        if not domanda:
            risposta = None
        elif not utente:
            risposta = ("Ciao! Sono la stylist di Up Collection. Accedi o crea un account "
                        "e ti aiuto a scegliere capi, taglie e abbinamenti dal nostro catalogo.")
        elif not current_app.config.get("GROQ_API_KEY"):
            risposta = "La stylist non è ancora attiva: manca GROQ_API_KEY nel file .env."
        else:
            # il catalogo diventa un elenco di righe che l'IA può consultare
            catalogo = "\n".join(
                "- " + p["nome"] + " | " + p["marca"] + " | " + p["categoria"] + " | "
                + p["tipo"] + " | " + p["colore"] + " | " + str(p["prezzo"]) + " euro"
                + " | taglie " + (p["taglie"] or "unica")
                for p in leggi_prodotti()
                if p["quantita"] > 0
            )
            try:
                from groq import Groq
                client = Groq(api_key=current_app.config["GROQ_API_KEY"])
                risultato = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": (
                            "Sei la stylist di Up Collection, negozio di abbigliamento uomo e donna "
                            "a Torino dagli anni '60. Rispondi in italiano, con tono caldo e breve "
                            "(massimo 6 frasi). Consiglia SOLO capi di questo catalogo, citando nome "
                            "e prezzo. Non dire di aver fatto acquisti o modifiche.\n\nCatalogo:\n"
                            + catalogo)},
                        {"role": "user", "content": domanda},
                    ],
                    temperature=0.5,
                    max_tokens=400,
                )
                risposta = risultato.choices[0].message.content
            except Exception:
                risposta = "Non riesco a contattare la stylist in questo momento. Riprova tra poco."
    return render_template("stylist.html", domanda=domanda, risposta=risposta)


# ADMIN

@shop.route("/admin")
@role_required("admin")
def admin():
    return render_template(
        "admin/dashboard.html",
        numeri=statistiche(),
        ultimi=leggi_ordini()[:6],
        scorte=scorte_basse(2),
    )


@shop.route("/admin/prodotti")
@role_required("admin")
def admin_prodotti():
    ricerca = request.args.get("q", "").strip()
    return render_template("admin/prodotti.html",
                           prodotti=leggi_prodotti(ricerca=ricerca), q=ricerca)


def dati_prodotto_dal_form():
    """Legge e controlla i campi del form prodotto (stesso form per aggiungi e modifica)."""
    dati = {
        "nome": request.form.get("nome", "").strip(),
        "marca": request.form.get("marca", "").strip(),
        "categoria": request.form.get("categoria", ""),
        "tipo": request.form.get("tipo", "").strip(),
        "colore": request.form.get("colore", "").strip(),
        "descrizione": request.form.get("descrizione", "").strip(),
        "prezzo": request.form.get("prezzo", type=float),
        # "XS, S , M" -> "XS,S,M"
        "taglie": ",".join(t.strip() for t in request.form.get("taglie", "").split(",") if t.strip()),
        # un indirizzo per riga -> separati da virgola
        "immagini": ",".join(r.strip() for r in request.form.get("immagini", "").splitlines() if r.strip()),
        "quantita": request.form.get("quantita", type=int),
        "novita": 1 if request.form.get("novita") else 0,
    }
    errore = None
    if not dati["nome"] or not dati["marca"] or not dati["tipo"]:
        errore = "Nome, marca e tipo sono obbligatori."
    elif dati["categoria"] not in ("donna", "uomo"):
        errore = "Scegli Donna o Uomo."
    elif dati["prezzo"] is None or dati["prezzo"] < 0 or dati["quantita"] is None or dati["quantita"] < 0:
        errore = "Controlla prezzo e quantità."
    return dati, errore


@shop.route("/admin/prodotti/aggiungi", methods=["GET", "POST"])
@role_required("admin")
def aggiungi_prodotto():
    if request.method == "POST":
        dati, errore = dati_prodotto_dal_form()
        if errore:
            flash(errore, "error")
            return render_template("admin/form_prodotto.html", p=dati, nuovo=True,
                                   tipi=leggi_tipi(), marche=leggi_marche())
        inserisci_prodotto(**dati)
        flash("Prodotto inserito.", "success")
        return redirect(url_for("shop.admin_prodotti"))
    return render_template("admin/form_prodotto.html", p=None, nuovo=True,
                           tipi=leggi_tipi(), marche=leggi_marche())


@shop.route("/admin/prodotti/modifica/<int:id>", methods=["GET", "POST"])
@role_required("admin")
def modifica_prodotto_route(id):
    p = trova_prodotto(id)
    if not p:
        flash("Prodotto non trovato.", "error")
        return redirect(url_for("shop.admin_prodotti"))
    if request.method == "POST":
        dati, errore = dati_prodotto_dal_form()
        if errore:
            flash(errore, "error")
        else:
            modifica_prodotto(id, **dati)
            flash("Prodotto aggiornato.", "success")
            return redirect(url_for("shop.admin_prodotti"))
    return render_template("admin/form_prodotto.html", p=p, nuovo=False,
                           tipi=leggi_tipi(), marche=leggi_marche())


# DELETE in due passaggi: GET chiede conferma, POST cancella
@shop.route("/admin/prodotti/elimina/<int:id>")
@role_required("admin")
def elimina_prodotto_route(id):
    p = trova_prodotto(id)
    if not p:
        flash("Prodotto non trovato.", "error")
        return redirect(url_for("shop.admin_prodotti"))
    return render_template("admin/elimina_prodotto.html", p=p)


@shop.route("/admin/prodotti/elimina/<int:id>", methods=["POST"])
@role_required("admin")
def elimina_prodotto_conferma(id):
    elimina_prodotto(id)
    flash("Prodotto eliminato.", "success")
    return redirect(url_for("shop.admin_prodotti"))


@shop.route("/admin/ordini")
@role_required("admin")
def admin_ordini():
    stato = request.args.get("stato", "")
    return render_template("admin/ordini.html", ordini=leggi_ordini(stato),
                           stati=STATI_ORDINE, stato=stato)


@shop.route("/admin/ordini/<int:id>/stato", methods=["POST"])
@role_required("admin")
def cambia_stato_ordine(id):
    stato = request.form.get("stato", "")
    if stato in STATI_ORDINE and trova_ordine(id):
        modifica_stato_ordine(id, stato)
        flash("Ordine #" + str(id) + ": " + stato + ".", "success")
    return redirect(url_for("shop.scheda_ordine", id=id))


@shop.route("/admin/messaggi")
@role_required("admin")
def admin_messaggi():
    return render_template("admin/messaggi.html", messaggi=leggi_messaggi())


@shop.route("/admin/messaggi/elimina/<int:id>", methods=["POST"])
@role_required("admin")
def elimina_messaggio_route(id):
    elimina_messaggio(id)
    flash("Messaggio eliminato.", "success")
    return redirect(url_for("shop.admin_messaggi"))
