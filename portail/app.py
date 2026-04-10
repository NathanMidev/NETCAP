from flask import Flask, request, redirect, render_template
from session_manager import SessionManager

app = Flask(__name__)

session_manager = SessionManager()


@app.route("/portail", methods=["GET", "POST"])
def portail():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Authentification simple (pour test)
        if username == "admin" and password == "1234":

            # récupérer IP client
            ip = request.remote_addr

            # créer session
            session_manager.create_session(ip)

            # redirection vers site demandé
            redirect_url = request.args.get("redirect_url")

            if redirect_url:
                return redirect(redirect_url)

            return "Authentifié"

        return "Erreur login"

    return render_template("login.html")


if __name__ == "__main__":
    app.run(port=5000)