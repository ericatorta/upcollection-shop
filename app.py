"""
Up Collection – e-commerce in Flask (struttura MVC)

    app.py                      crea l'app e registra il blueprint
    config.py                   classe Config (chiave segreta, database, Groq, dati negozio)
    models/database.py          tutte le query SQL
    models/prodotti_demo.py     catalogo di esempio caricato al primo avvio
    controllers/controller.py   tutte le route (Blueprint "shop")
    templates/                  pagine HTML (Jinja)
    static/                     css, font, icona
"""
from flask import Flask, render_template
from config import Config
from models.database import crea_database
from controllers.controller import shop


def create_app():
    app = Flask(__name__)
    # carica SECRET_KEY, DATABASE, GROQ_API_KEY e i dati del negozio
    app.config.from_object(Config)
    # crea le tabelle (e il catalogo demo) al primo avvio
    crea_database()
    # senza questa riga le route del controller non esistono
    app.register_blueprint(shop)

    @app.template_filter("euro")
    def euro(valore):
        # 1234.5 -> "1.234,50 €" (formato italiano)
        testo = "{:,.2f}".format(valore or 0)
        return testo.replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    @app.context_processor
    def dati_comuni():
        # disponibili in tutti i template: dati del negozio
        return {"negozio": Config.NEGOZIO, "soglia_gratis": Config.SOGLIA_SPEDIZIONE_GRATIS}

    @app.errorhandler(404)
    def pagina_non_trovata(errore):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    # modalità debug per lo sviluppo
    app.run(debug=True)
