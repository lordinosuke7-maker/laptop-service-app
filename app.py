from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask import session
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","default_secret_key") # you can change this

# SQLite database in the project folder
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "service.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    laptop_model = db.Column(db.String(100), nullable=False)
    problem = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            session["admin"] = True
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    # --- ADMIN LOGIN PROTECTION ---
    if "admin" not in session:
        return redirect(url_for("login"))

    # --- SEARCH & FILTER ---
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    tickets = Ticket.query

    if q:
        tickets = tickets.filter(
            (Ticket.customer_name.ilike(f"%{q}%")) |
            (Ticket.laptop_model.ilike(f"%{q}%")) |
            (Ticket.problem.ilike(f"%{q}%"))
        )

    if status_filter:
        tickets = tickets.filter(Ticket.status == status_filter)

    tickets = tickets.order_by(Ticket.id.desc()).all()

    return render_template("index.html", tickets=tickets)

@app.route("/add", methods=["GET", "POST"])
def add_ticket():
    if request.method == "POST":
        name = request.form["name"]
        model = request.form["model"]
        issue = request.form["issue"]

        new_ticket = Ticket(
            customer_name=name,
            laptop_model=model,
            problem=issue,
            status="Pending"
        )

        db.session.add(new_ticket)
        db.session.commit()
        return redirect(url_for("index"))
    
    return render_template("add_ticket.html")


@app.route("/update_status/<int:ticket_id>", methods=["POST"])
def update_status(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = request.form["status"]
    db.session.commit()
    return redirect(url_for("index"))

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

@app.route("/export_pdf")
def export_pdf():
    tickets = Ticket.query.order_by(Ticket.id.asc()).all()

    file_path = "tickets.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)

    y = 750
    c.setFont("Helvetica", 12)
    c.drawString(200, 780, "Laptop Service Tickets Report")

    for t in tickets:
        c.drawString(50, y, f"ID: {t.id} | Name: {t.customer_name} | Model: {t.laptop_model} | Issue: {t.problem} | Status: {t.status}")
        y -= 20

        if y < 50:  
            c.showPage()
            y = 750

    c.save()

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # creates the service.db file if not there
    app.run(debug=True)
