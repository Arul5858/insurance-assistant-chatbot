import os
import re
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///insurance_assistant.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    profile = db.relationship("InsuranceProfile", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class InsuranceProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    current_step = db.Column(db.Integer, default=0, nullable=False)
    age = db.Column(db.Integer)
    insurance_type = db.Column(db.String(60))
    budget_period = db.Column(db.String(20))
    budget_amount = db.Column(db.Numeric(14, 2))
    coverage_amount = db.Column(db.String(100))
    has_existing_policy = db.Column(db.String(10))
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(500), default="")
    category = db.Column(db.String(100), default="General")
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    conversation_id = db.Column(db.String(36), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(30), default="system")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


DEFAULT_FAQS = [
    ("What types of insurance are available?", "Common insurance categories include life, health, motor, travel, and home insurance. Availability, eligibility, benefits, exclusions, and prices depend on the insurer and specific product.", "insurance types, products, life, health, motor, travel, home", "Products"),
    ("How can I buy an insurance policy?", "Start by identifying the cover you need, compare the policy benefits, exclusions, limits, and premium, and review the policy wording. Complete the application through an authorized insurer or representative.", "buy, purchase, apply, new policy", "Policies"),
    ("How can I check my policy status?", "Use your insurer's official customer portal or contact its customer-support team with your policy number. Do not share passwords or OTPs in this chat.", "policy status, active policy, check policy", "Policies"),
    ("How do I pay my insurance premium?", "Use only the official payment channel provided by your insurer. Verify the website and keep your payment receipt. This demo assistant does not collect or process payments.", "premium, pay, payment, due", "Payments"),
    ("How can I renew my policy?", "Check your policy schedule for the renewal date and follow the insurer's official renewal instructions. Confirm the premium and terms before paying.", "renew, renewal, renew policy, expiry", "Renewals"),
    ("How do I file an insurance claim?", "Notify your insurer as soon as possible and follow its claim procedure. Keep your policy details, claim form, incident information, and supporting documents ready. Requirements and timelines depend on your policy.", "claim, file claim, claim process, reimbursement", "Claims"),
    ("What documents are required for a claim?", "Documents vary by policy and claim type. They may include policy details, a claim form, identity proof, bills, reports, and incident-related records. Ask your insurer for the exact checklist.", "claim documents, documents, proof, bills", "Claims"),
    ("What is a waiting period in health insurance?", "A waiting period is a specified period during which certain conditions or treatments may not be covered. The duration and applicable conditions depend on the policy wording.", "waiting period, health insurance, coverage start", "Health Insurance"),
    ("Does this assistant calculate my premium?", "No. This assistant collects your budget preferences to help understand your needs, but it does not calculate a binding premium or issue an insurance quotation.", "calculate premium, quote, premium amount, cost", "Products"),
    ("Is my information safe?", "This is a demonstration application. Avoid entering passwords, OTPs, bank details, full card numbers, or unnecessary medical or identity information. Production use requires a privacy and security review.", "privacy, secure, personal data, information safe", "Privacy"),
]

ONBOARDING_QUESTIONS = [
    {"key": "age", "question": "What is your age?", "hint": "Enter your age in years (18–100).", "kind": "number"},
    {"key": "insurance_type", "question": "What type of insurance do you need?", "hint": "Choose the type that best matches your needs.", "kind": "choice", "options": ["Health Insurance", "Life Insurance", "Motor Insurance", "Travel Insurance", "Home Insurance", "Other / Not sure"]},
    {"key": "budget", "question": "What is your monthly or annual budget?", "hint": "Choose a period and enter an approximate amount in INR.", "kind": "budget"},
    {"key": "coverage_amount", "question": "What coverage amount are you looking for?", "hint": "For example: ₹5 lakh, ₹10 lakh, or not sure yet.", "kind": "text"},
    {"key": "has_existing_policy", "question": "Do you already have an insurance policy?", "hint": "Choose Yes or No.", "kind": "choice", "options": ["Yes", "No"]},
]


def normalize(text):
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower()).strip()


def find_faq_answer(user_text):
    query = normalize(user_text)
    if not query:
        return None
    query_words = set(query.split())
    best_score, best_faq = 0.0, None
    for faq in FAQ.query.filter_by(active=True).all():
        question = normalize(faq.question)
        keywords = [w for w in normalize(faq.keywords).split() if len(w) > 2]
        faq_words = set(question.split()) | set(keywords)
        overlap = len(query_words & faq_words)
        coverage = overlap / max(1, len(query_words))
        similarity = SequenceMatcher(None, query, question).ratio()
        keyword_hits = sum(1 for word in keywords if word in query)
        score = max(similarity, coverage * 0.78) + min(keyword_hits * 0.07, 0.28)
        if score > best_score:
            best_score, best_faq = score, faq
    return best_faq.answer if best_faq and best_score >= 0.34 else None


def save_message(conversation_id, role, message, source):
    db.session.add(ChatMessage(user_id=current_user.id, conversation_id=conversation_id,
                               role=role, message=message[:5000], source=source))
    db.session.commit()


def get_ai_reply(user_text, conversation_id):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=api_key)
        recent = (ChatMessage.query.filter_by(user_id=current_user.id, conversation_id=conversation_id)
                  .order_by(ChatMessage.created_at.desc()).limit(8).all())
        recent.reverse()
        profile = current_user.profile
        profile_context = ""
        if profile and profile.completed_at:
            profile_context = (f" User preferences: age {profile.age}; insurance type {profile.insurance_type}; "
                               f"budget {profile.budget_amount} INR per {profile.budget_period}; "
                               f"desired coverage {profile.coverage_amount}; existing policy {profile.has_existing_policy}.")
        messages = [{"role": "system", "content": (
            "You are a helpful, neutral Insurance Assistant. Explain general insurance concepts in simple language. "
            "Use the customer's preferences only to frame general guidance; do not treat them as a quote or eligibility decision. "
            "Never invent insurer product terms, prices, policy status, claim status, or contact details. "
            "Do not approve/reject claims, sell policies, calculate binding premiums, or process payments. "
            "For personal policy or claim records, direct the user to their authenticated insurer portal or insurer support. "
            "Do not request passwords, OTPs, bank credentials, full card numbers, or unnecessary sensitive information. "
            "State uncertainty clearly and advise checking official policy wording." + profile_context
        )}]
        for item in recent:
            if item.role in ("user", "assistant"):
                messages.append({"role": item.role, "content": item.message[:2500]})
        messages.append({"role": "user", "content": user_text[:2500]})
        result = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                                                messages=messages, temperature=0.3, max_tokens=450)
        return result.choices[0].message.content.strip()
    except Exception:
        app.logger.exception("AI request failed")
        return None


@app.route("/")
def home():
    return redirect(url_for("chat") if current_user.is_authenticated and current_user.profile and current_user.profile.completed_at
                    else url_for("onboarding") if current_user.is_authenticated else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not full_name or len(full_name) > 120:
            flash("Please enter your name.", "danger")
        elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
            flash("Please enter a valid email address.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please log in.", "warning")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            user = User(full_name=full_name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            db.session.add(InsuranceProfile(user_id=user.id))
            db.session.commit()
            login_user(user)
            session["conversation_id"] = str(uuid.uuid4())
            flash("Your account has been created. Let's understand your insurance needs.", "success")
            return redirect(url_for("onboarding"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get("remember") == "on")
            session["conversation_id"] = str(uuid.uuid4())
            return redirect(url_for("home"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.get("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/onboarding")
@login_required
def onboarding():
    profile = current_user.profile
    if profile is None:
        profile = InsuranceProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
    if profile.completed_at:
        return redirect(url_for("chat"))
    return render_template("onboarding.html", profile=profile, questions=ONBOARDING_QUESTIONS,
                           first_name=current_user.full_name.split()[0])


@app.post("/api/onboarding/answer")
@login_required
def onboarding_answer():
    data = request.get_json(silent=True) or {}
    profile = current_user.profile
    if profile is None:
        profile = InsuranceProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.flush()
    if profile.completed_at:
        return jsonify({"complete": True, "redirect": url_for("chat")})
    step = profile.current_step
    if step < 0 or step >= len(ONBOARDING_QUESTIONS):
        return jsonify({"error": "Questionnaire state is invalid. Please refresh."}), 400
    value = data.get("value")
    question = ONBOARDING_QUESTIONS[step]

    if step == 0:
        try:
            age = int(value)
        except (TypeError, ValueError):
            return jsonify({"error": "Please enter your age as a whole number."}), 400
        if age < 18 or age > 100:
            return jsonify({"error": "Please enter an age between 18 and 100."}), 400
        profile.age = age
    elif step == 1:
        allowed = ONBOARDING_QUESTIONS[1]["options"]
        if value not in allowed:
            return jsonify({"error": "Please choose one of the listed insurance types."}), 400
        profile.insurance_type = value
    elif step == 2:
        period = data.get("period")
        if period not in ("monthly", "annual"):
            return jsonify({"error": "Please choose monthly or annual."}), 400
        try:
            amount = Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, AttributeError):
            return jsonify({"error": "Please enter a valid budget amount."}), 400
        if amount <= 0 or amount > Decimal("1000000000"):
            return jsonify({"error": "Please enter a budget greater than zero."}), 400
        profile.budget_period = period
        profile.budget_amount = amount
    elif step == 3:
        text = str(value or "").strip()
        if not text or len(text) > 100:
            return jsonify({"error": "Please enter a coverage amount or 'Not sure yet'."}), 400
        profile.coverage_amount = text
    elif step == 4:
        if value not in ("Yes", "No"):
            return jsonify({"error": "Please select Yes or No."}), 400
        profile.has_existing_policy = value

    profile.current_step += 1
    completed = profile.current_step >= len(ONBOARDING_QUESTIONS)
    if completed:
        profile.completed_at = datetime.utcnow()
    db.session.commit()

    if completed:
        return jsonify({"complete": True, "message": f"Thank you, {current_user.full_name.split()[0]}! I have saved your answers. You can now ask me insurance questions.", "redirect": url_for("chat")})
    return jsonify({"complete": False, "next_step": profile.current_step,
                    "question": ONBOARDING_QUESTIONS[profile.current_step]})


@app.get("/chat")
@login_required
def chat():
    profile = current_user.profile
    if not profile or not profile.completed_at:
        return redirect(url_for("onboarding"))
    if "conversation_id" not in session:
        session["conversation_id"] = str(uuid.uuid4())
    return render_template("chat.html", first_name=current_user.full_name.split()[0], profile=profile)


@app.post("/api/chat")
@login_required
def chat_api():
    profile = current_user.profile
    if not profile or not profile.completed_at:
        return jsonify({"error": "Please complete your insurance profile first."}), 403
    data = request.get_json(silent=True) or {}
    user_text = (data.get("message") or "").strip()
    if not user_text:
        return jsonify({"error": "Please enter a message."}), 400
    if len(user_text) > 2000:
        return jsonify({"error": "Please keep your message under 2,000 characters."}), 400
    conversation_id = session.setdefault("conversation_id", str(uuid.uuid4()))
    save_message(conversation_id, "user", user_text, "customer")
    answer = find_faq_answer(user_text)
    if answer:
        source = "faq"
    else:
        answer = get_ai_reply(user_text, conversation_id)
        if answer:
            source = "ai"
        else:
            source = "fallback"
            answer = ("I couldn't find a suitable answer in the FAQ knowledge base, and AI assistance is currently unavailable. "
                      "Please try asking about insurance types, policy renewal, premiums, or claims, or contact your insurer directly.")
    save_message(conversation_id, "assistant", answer, source)
    return jsonify({"reply": answer, "source": source})


@app.get("/api/history")
@login_required
def chat_history():
    conversation_id = session.get("conversation_id")
    if not conversation_id:
        return jsonify({"messages": []})
    rows = (ChatMessage.query.filter_by(user_id=current_user.id, conversation_id=conversation_id)
            .order_by(ChatMessage.created_at.asc()).limit(100).all())
    return jsonify({"messages": [{"role": m.role, "message": m.message, "source": m.source,
                                  "time": m.created_at.strftime("%H:%M")} for m in rows]})


@app.post("/api/new-chat")
@login_required
def new_chat():
    session["conversation_id"] = str(uuid.uuid4())
    return jsonify({"ok": True})


@app.get("/profile")
@login_required
def profile():
    return render_template("profile.html", profile=current_user.profile)


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    if FAQ.query.count() == 0:
        for question, answer, keywords, category in DEFAULT_FAQS:
            db.session.add(FAQ(question=question, answer=answer, keywords=keywords, category=category))
        db.session.commit()
    print("Database initialized. Starter FAQs are ready.")


@app.cli.command("reset-onboarding")
@login_required
def reset_onboarding_command():
    """Not intended for CLI use; use the profile reset route if added later."""
    print("Use the customer profile page to review your saved preferences.")


if __name__ == "__main__":
    app.run(debug=True)
