import os, uuid, io
print("==========================================", flush=True)
print("🚀 QuickNewsAI is starting up...", flush=True)
print("==========================================", flush=True)

# 🛡️ DB INITIALIZATION moved below app definition

from flask import Flask, render_template, request, redirect, jsonify, send_file, session, flash, url_for
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import date, timedelta

from gtts import gTTS
from services.logger import logger
from services.news_api import fetch_latest_news
from services.extractor import extract_news_from_url
from services.summarizer import summarize_text
from services.translator import translate_summary, translate_full_news
from services.history import (
    save_news_safe, get_all_history, get_history_by_id, delete_history_by_id,
    get_language_stats, get_length_stats, get_sentiment_stats, get_activity_stats,
    save_translation, save_latest_news_bulk, increase_open_count,
    toggle_bookmark, get_bookmarks, is_bookmarked, save_rating,
    get_average_rating, get_user_rating, auto_categorize, get_history_with_categories,
    save_email_preference, get_email_preference,
)
from services.utils import calculate_read_time
from services.sentiment import analyze_sentiment
from services.auth import (
    login_user, register_user, create_users_table, create_otp_table,
    verify_email_otp, send_otp, send_reset_otp, reset_password_with_otp
)
from services.profile import get_user_profile, update_user_profile, delete_user_account
from services.email_digest import send_digests, run_periodic_digest
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.secret_key = "quicknews_secret_key"

# 🚩 DB INITIALIZATION FLAG
_db_initialized = False

@app.before_request
def ensure_db_init():
    global _db_initialized
    if not _db_initialized:
        print("🛠️ DEFERRED DB INITIALIZATION STARTING...", flush=True)
        from init_db import init_postgres_db
        try:
            init_postgres_db()
            _db_initialized = True
            print("🚀 DEFERRED DB INITIALIZATION SUCCESS!", flush=True)
        except Exception as e:
            print(f"🔥 DEFERRED DB INITIALIZATION FAILED: {e}", flush=True)

@app.route("/")
def index():
    return redirect(url_for("login"))

# ==================================================
# AUTH GUARD
# ==================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("🚫 Access denied. Admins only.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

# ==================================================
# LOGIN / REGISTER / LOGOUT
# ==================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in → go home
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    active_tab = "login"

    if request.method == "POST":
        form_type = request.form.get("form_type", "login")

        if form_type == "login":
            name_or_email = request.form.get("username_or_email", "").strip()
            password = request.form.get("password", "")

            try:
                user = login_user(name_or_email, password)
                if user:
                    session["user_id"] = user["user_id"]
                    session["name"] = user["name"]
                    session["role"] = user["role"]
                    
                    # Load profile for picture
                    prof = get_user_profile(user["user_id"])
                    if prof:
                        session["profile_pic"] = prof["profile_pic"]
                        
                    if user["role"] == "admin":
                        return redirect(url_for("admin_panel"))
                    return redirect(url_for("dashboard"))
                else:
                    flash("❌ Invalid username/email or password.", "error")
            except ValueError as ve:
                flash(f"❌ {ve}", "error")

        elif form_type == "register":
            active_tab = "register"
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            if len(password) < 6:
                flash("❌ Password must be at least 6 characters.", "error")
            else:
                try:
                    register_user(username, email, password)
                    send_otp(email)
                    flash("✅ Account created! Please verify your email with the OTP sent.", "success")
                    return redirect(url_for("verify_otp", email=email))
                except ValueError as ve:
                    flash(f"❌ {ve}", "error")

    return render_template("login.html", active_tab=active_tab)

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = request.args.get("email") or request.form.get("email")
    if not email:
        flash("❌ Missing email.", "error")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        if verify_email_otp(email, otp):
            flash("✅ Email verified successfully! You can now login.", "success")
            return redirect(url_for("login"))
        else:
            flash("❌ Invalid OTP. Please try again.", "error")
            
    return render_template("verify_otp.html", email=email)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        try:
            send_reset_otp(email)
            flash("✅ OTP sent! Please check your email and enter it below.", "success")
            return redirect(url_for("verify_reset_otp", email=email))
        except Exception as e:
            flash(f"❌ Error: {e}", "error")
            return redirect(url_for("forgot_password"))
    return render_template("forgot_password.html")

@app.route("/verify-reset-otp", methods=["GET", "POST"])
def verify_reset_otp():
    email = request.args.get("email") or request.form.get("email")
    if not email:
        flash("❌ Missing email.", "error")
        return redirect(url_for("forgot_password"))
    
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        if verify_email_otp(email, otp, delete_after=False):
            return redirect(url_for("reset_password", email=email, otp=otp))
        else:
            flash("❌ Invalid OTP. Please try again.", "error")
            
    return render_template("verify_reset_otp.html", email=email)

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email") or request.form.get("email")
    otp = request.args.get("otp") or request.form.get("otp")
    if not email or not otp:
        flash("❌ Session expired or invalid request.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password", "")
        if len(new_password) < 6:
            flash("❌ Password must be at least 6 characters.", "error")
            return render_template("reset_password.html", email=email, otp=otp)
        
        if reset_password_with_otp(email, otp, new_password):
            flash("✅ Password reset successful! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("❌ Error resetting password. OTP might be invalid.", "error")
            return redirect(url_for("forgot_password"))
            
    return render_template("reset_password.html", email=email, otp=otp)

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ You have been logged out.", "success")
    return redirect(url_for("login"))

# ==================================================
# ADMIN PANEL
# ==================================================
@app.route("/admin")
@admin_required
def admin_panel():
    from services.auth import get_all_users
    from services.history import get_global_stats
    
    search = request.args.get("search", "").strip()
    
    # Fetch all users
    users = get_all_users()
    
    # Basic search filter
    if search:
        users = [u for u in users if search.lower() in u['name'].lower() or search.lower() in u['email'].lower()]
        
    stats = get_global_stats()
    
    return render_template("admin.html", users=users, stats=stats, search_query=search)

@app.route("/admin/news")
@admin_required
def admin_news():
    from services.history import get_admin_news_history
    search = request.args.get("search", "").strip()
    news_list = get_admin_news_history(search=search)
    return render_template("admin_news.html", news_list=news_list, search_query=search)

@app.route("/admin/news/delete/<int:news_id>", methods=["POST"])
@admin_required
def admin_delete_news(news_id):
    from services.history import delete_history_by_id
    delete_history_by_id(news_id)
    flash("✅ News summary deleted successfully.", "success")
    return redirect(url_for("admin_news"))


@app.route("/admin/toggle_status/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_status(user_id):
    from services.auth import toggle_user_status
    if user_id == session.get("user_id"):
        flash("❌ You cannot block your own account.", "error")
    else:
        toggle_user_status(user_id)
        flash(f"✅ User status toggled.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    from services.auth import delete_user
    if user_id == session.get("user_id"):
        flash("❌ You cannot delete your own account.", "error")
    else:
        try:
            delete_user(user_id)
            flash(f"✅ User deleted successfully.", "success")
        except ValueError as e:
            flash(f"❌ {e}", "error")
        except Exception as e:
            flash(f"❌ Error deleting user: {e}", "error")
    return redirect(url_for("admin_panel"))


# ==================================================
# PROFILE
# ==================================================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    user_id = session.get("user_id")
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        
        # Handle file upload
        file = request.files.get("profile_pic")
        filename = None
        
        if file and file.filename != "":
            # Basic security for filenames
            filename = secure_filename(f"user_{user_id}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            
            # Update session pic immediately
            session["profile_pic"] = filename
            
        try:
            update_user_profile(
                user_id=user_id,
                name=name,
                email=email,
                current_password=current_password if current_password else None,
                new_password=new_password if new_password else None,
                profile_pic_filename=filename
            )
            session["name"] = name  # update display name
            flash("✅ Profile updated successfully!", "success")
        except ValueError as e:
            flash(f"❌ {str(e)}", "error")
            
        return redirect(url_for("profile"))
        
    user_profile = get_user_profile(user_id)
    current_digest = get_email_preference(user_id)
    return render_template("profile.html", profile=user_profile, current_digest=current_digest)
# ==================================================
# DASHBOARD
# ==================================================
@app.route("/", methods=["GET", "POST"])
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))

    from services.history import get_user_dashboard_stats, get_recent_history

    full_news = ""
    summary = ""
    read_time = ""
    sentiment = None
    user_id = session.get("user_id")

    # Fetch Stats & Recent History
    stats = get_user_dashboard_stats(user_id)
    recent_history = get_recent_history(user_id, limit=3)

    if request.method == "POST":
        url = request.form.get("news_url")
        selected_lang = request.form.get("language", "en")
        length_value = request.form.get("summary_length", "medium")

        if length_value == "short":
            summary_length = 80
        elif length_value == "long":
            summary_length = 250
        else:
            summary_length = 150

        data = extract_news_from_url(url)
        if data and data.get("text"):
            title = data.get("title") or "News Article"
            original_news = data.get("text")
            english_article = translate_full_news(original_news, "en")
            english_summary = summarize_text(english_article, summary_length)
            read_time = calculate_read_time(english_summary)
            sentiment = analyze_sentiment(english_summary)

            if selected_lang == "en":
                full_news = english_article
                summary = english_summary
            else:
                full_news = translate_full_news(original_news, selected_lang)
                summary = translate_summary(english_summary, selected_lang)

            save_news_safe(
                user_id,
                title,
                url,
                full_news,
                summary,
                selected_lang,
                summary_length,
                sentiment["label"],
                sentiment.get("score", 0.0)
            )
            # Update stats after new summary
            stats = get_user_dashboard_stats(user_id)
            recent_history = get_recent_history(user_id, limit=3)

    return render_template(
        "dashboard.html",
        full_news=full_news,
        summary=summary,
        read_time=read_time,
        sentiment=sentiment,
        user_name=session.get("name", "User"),
        stats=stats,
        recent_history=recent_history
    )

# ==================================================
@app.route("/api/news")
def api_news():
    page = request.args.get("page", 1)
    data = fetch_latest_news(page=page)
    return jsonify(data)

@app.route("/news")
@login_required
def news():
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    page = request.args.get("page", 1)
    category = request.args.get("category", "general")

    page_size = 12

    data = fetch_latest_news(
        page=page,
        page_size=page_size,
        category=category
    )
    news_list = data.get("results", [])
    next_page = data.get("nextPage")

    # ✅ Save fetched articles to latest_news table
    try:
        save_latest_news_bulk(news_list)
    except Exception as e:
        logger.error(f"latest_news save error: {e}")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"results": news_list, "nextPage": next_page})

    return render_template(
        "latest_news.html",
        news_list=news_list,
        next_page=next_page,
        current_category=category
    )

@app.route("/open_news")
def open_news():
    url = request.args.get("url")
    return redirect(url)



@app.route("/api/summary")
def api_summary():
    url = request.args.get("url")
    lang = request.args.get("lang", "en")

    # 🔥 Normalize language
    lang_map = {
        "english": "en",
        "gujarati": "gu",
        "hindi": "hi"
    }

    lang = lang_map.get(lang.lower(), lang)

    print("LANG RECEIVED:", lang)

    data = extract_news_from_url(url)
    if not data or not data.get("text"):
        return {"error": "Unable to extract"}

    original_text = data["text"]

    english_article = translate_full_news(original_text, "en")

    if not english_article or len(english_article.strip()) < 30:
        english_article = original_text

    english_summary = summarize_text(english_article, 150)

    if lang == "en":
        final_news = english_article
        final_summary = english_summary
    else:
        final_news = translate_full_news(english_article, lang)
        final_summary = translate_summary(english_summary, lang)

    # ✅ Save translation to DB (no summary_id for latest news — use 0 as default)
    try:
        if lang != "en":
            save_translation(
                summary_id=0,
                source_language="en",
                target_language=lang,
                translated_text=final_summary
            )
    except Exception as e:
        logger.error(f"Translation DB error: {e}")

    return {
        "summary": final_summary,
        "full_news": final_news
    }
# ==================================================
@app.route("/api/translate")
def api_translate():
    text = request.args.get("text", "")
    lang = request.args.get("lang", "en")
    summary_id = request.args.get("summary_id", 0)

    if not text:
        return {"error": "Text missing"}

    translated = translate_summary(text, lang)

    # ✅ Save translation to DB
    try:
        save_translation(
            summary_id=int(summary_id),
            source_language="en",
            target_language=lang,
            translated_text=translated
        )
    except Exception as e:
        logger.error(f"Translation DB error: {e}")

    return {"translated": translated}

# ==================================================
# TEXT TO SPEECH (LATEST NEWS ONLY)
# ==================================================
@app.route("/tts")
def tts():
    text = request.args.get("text", "")
    lang = request.args.get("lang", "en")

    if not text:
        return "No text", 400

    tts = gTTS(text=text, lang=lang)
    audio_io = io.BytesIO()
    tts.write_to_fp(audio_io)
    audio_io.seek(0)

    return send_file(
        audio_io,
        mimetype="audio/mpeg",
        as_attachment=False
    )

# ==================================================
# EMAIL DIGEST SEND (ADMIN MANUAL)
# ==================================================
@app.route("/admin/send-daily-digest", methods=["POST"])
@login_required
@admin_required
def admin_send_daily_digest():
    try:
        sent = send_digests("daily")
        flash(f"✅ Daily digest cycle complete. {sent} emails sent.", "success")
    except Exception as e:
        flash(f"❌ Digest error: {e}", "error")
    return redirect(url_for("admin_panel"))

@app.route("/admin/send-weekly-digest", methods=["POST"])
@login_required
@admin_required
def admin_send_weekly_digest():
    try:
        sent = send_digests("weekly")
        flash(f"✅ Weekly digest cycle complete. {sent} emails sent.", "success")
    except Exception as e:
        flash(f"❌ Digest error: {e}", "error")
    return redirect(url_for("admin_panel"))

# ==================================================
# HISTORY
# ==================================================
@app.route("/history")
@login_required
def history():
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    user_id = session.get("user_id")
    records_with_cats = get_history_with_categories(user_id)
    records = []

    for r in records_with_cats:
        raw_len = r["summary_length"]
        summary_type = "Medium"

        try:
            raw_len = int(raw_len)
            if raw_len <= 100:
                summary_type = "Short"
            elif raw_len >= 200:
                summary_type = "Long"
        except:
            pass

        records.append({
            "id": r["id"],
            "title": r["title"],
            "language": r["language"],
            "summary_type": summary_type,
            "date": r["date"],
            "category": r["category"],
        })

    bookmarks = get_bookmarks(user_id)
    return render_template("history.html", records=records, bookmarks=bookmarks)

@app.route("/history/<int:news_id>")
@login_required
def view_history(news_id):
    user_id = session.get("user_id")
    record = get_history_by_id(news_id)
    user_rating = get_user_rating(user_id, news_id) if record else None
    category = auto_categorize(record[2] if record else "")  # record[2] = full_news? no, record[1]=summary
    # record: (title, summary, full_news, url)
    category = auto_categorize(record[1] if record else "")
    return render_template("view_history.html", record=record, news_id=news_id,
                           user_rating=user_rating, category=category)

@app.route("/history/delete/<int:news_id>")
@login_required
def delete_history(news_id):
    delete_history_by_id(news_id)
    flash("✅ History item deleted.", "success")
    return redirect("/history")

@app.route("/history/clear-all")
@login_required
def clear_all_history():
    from services.history import delete_all_history
    user_id = session.get("user_id")
    delete_all_history(user_id)
    flash("✅ All history cleared.", "success")
    return redirect("/history")

# ==================================================
# PHASE 2: BOOKMARKS
# ==================================================
@app.route("/bookmarks")
@login_required
def bookmarks():
    return redirect("/history")

@app.route("/api/bookmark", methods=["POST"])
@login_required
def api_bookmark():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    url = data.get("url", "")
    title = data.get("title", "")
    image_url = data.get("image_url", "")
    source_name = data.get("source_name", "")
    if not url:
        return jsonify({"error": "url required"}), 400
    added = toggle_bookmark(user_id, url, title, image_url, source_name)
    logger.info(f"Bookmark {'added' if added else 'removed'} for user {user_id}: {url[:60]}")
    return jsonify({"bookmarked": added})

# ==================================================
# PHASE 2: RATINGS
# ==================================================
@app.route("/api/rate", methods=["POST"])
@login_required
def api_rate():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    summary_id = data.get("summary_id")
    rating = data.get("rating")
    if not summary_id or not rating:
        return jsonify({"error": "summary_id and rating required"}), 400
    try:
        save_rating(user_id, int(summary_id), int(rating))
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Rating save error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================================================
# PHASE 2: RE-SUMMARIZE
# ==================================================
@app.route("/api/resummarize", methods=["POST"])
@login_required
def api_resummarize():
    data = request.get_json() or {}
    news_id = data.get("news_id")
    language = data.get("language", "en")
    length_label = data.get("length", "medium")

    length_map = {"short": 80, "medium": 150, "long": 250}
    summary_length = length_map.get(length_label.lower(), 150)

    record = get_history_by_id(news_id)
    if not record:
        return jsonify({"error": "Record not found"}), 404

    full_news = record[2]  # full_news
    try:
        # 🔥 Step 1: Ensure we have an English version for the AI model
        # The trained model in qnai_model is optimized for English.
        english_source = translate_full_news(full_news, "en")
        
        # Step 2: Summarize (English input -> English summary)
        english_summary = summarize_text(english_source, summary_length)
        
        # Step 3: Translate summary back to target language if needed
        if language != "en":
            final_summary = translate_summary(english_summary, language)
        else:
            final_summary = english_summary
            
        logger.info(f"Re-summarized news_id={news_id} lang={language} len={summary_length}")
        return jsonify({"summary": final_summary})
    except Exception as e:
        logger.error(f"Re-summarize error: {e}")
        return jsonify({"summary": "⚠️ AI error during re-summarization. The source text might be too complex or in a different format."})

# ==================================================
# PHASE 3: EMAIL PREFERENCES
# ==================================================
@app.route("/api/email-preference", methods=["POST"])
@login_required
def api_email_preference():
    user_id = session.get("user_id")
    data = request.get_json() or {}
    preference = data.get("preference", "off")
    if preference not in ("daily", "weekly", "off"):
        return jsonify({"error": "Invalid preference"}), 400
    try:
        save_email_preference(user_id, preference)
        return jsonify({"success": True, "preference": preference})
    except Exception as e:
        logger.error(f"Email preference save error: {e}")
        return jsonify({"error": str(e)}), 500

# Global pipeline cache (Lazy Loading)
QNA_PIPELINE = None
MODEL_LOAD_ERROR = False

def get_qna_pipeline():
    global QNA_PIPELINE, MODEL_LOAD_ERROR
    if QNA_PIPELINE or MODEL_LOAD_ERROR:
        return QNA_PIPELINE
        
    try:
        import os
        from transformers import pipeline, AutoConfig
        model_path = os.path.join(os.path.dirname(__file__), "qnai_model")
        
        if not (os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json"))):
            model_path = "Dev5808/QuickNewsAI-Model"
            
        config = AutoConfig.from_pretrained(model_path)
        m_type = getattr(config, "model_type", "").lower()
        
        if m_type in ["bart", "t5", "marian"]:
            QNA_PIPELINE = ("gen", pipeline("text2text-generation", model=model_path))
            logger.info(f"✅ Generative QnA Pipeline ({m_type}) loaded.")
        else:
            QNA_PIPELINE = ("ext", pipeline("question-answering", model=model_path))
            logger.info(f"✅ Extractive QnA Pipeline loaded.")
        return QNA_PIPELINE
    except Exception as e:
        logger.warning(f"Failed to load QnA model: {e}")
        MODEL_LOAD_ERROR = True
        return None

# ==================================================
# PHASE 4: QnA CHATBOT
# ==================================================
@app.route("/api/qna", methods=["POST"])
@login_required
def api_qna():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    context = data.get("context", "").strip()

    if not question:
        return jsonify({"answer": "Please provide a question."})

    # Use news context if present, otherwise just answer briefly
    # (Context might be small or full summary)
    
    # 🔥 STEP 1: Translate to English (Our AI is optimized for English)
    en_question = translate_summary(question, "en")
    en_context = translate_full_news(context, "en") if context else en_question
    
    pipe_info = get_qna_pipeline()
    answer = None

    if pipe_info:
        try:
            p_type, pipeline_obj = pipe_info
            if p_type == "gen":
                # Generative QnA (T5 / BART)
                prompt = f"question: {en_question} context: {en_context}"
                result = pipeline_obj(prompt, max_length=150, min_length=10, do_sample=False)
                answer = result[0].get("generated_text", "").strip()
            else:
                # Extractive QnA (BERT / RoBERTa)
                res = pipeline_obj(question=en_question, context=en_context)
                answer = res.get("answer", "").strip()
        except Exception as e:
            logger.error(f"Model inference failed: {e}")
    
    # STEP 2: Logic for translating back
    final_answer = answer if (answer and len(answer) > 2) else None

    # Fallback: Lightweight similarity matching if AI failed
    if not final_answer and context and len(context) > 20:
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', en_context) if len(s.strip()) > 10]
        if sentences:
            q_words = set(en_question.lower().split())
            best_sentence = None
            max_score = -1
            for s in sentences:
                s_words = set(s.lower().split())
                score = len(q_words & s_words)
                if score > max_score:
                    max_score = score
                    best_sentence = s
            if best_sentence and max_score > 1:
                final_answer = best_sentence

    if not final_answer:
        final_answer = "I'm sorry, I couldn't find a specific answer in this article. Try asking something else!"

    # 🔥 STEP 3: Translate back if the original question was likely Hindi/Gujarati
    if not any(w in question.lower() for w in ["what", "who", "where", "how", "is", "the", "can"]):
        # Support for Hindi/Gujarati users by translating English AI response back
        final_answer = translate_summary(final_answer, "hi")

    return jsonify({"answer": final_answer})

@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    user_id = session.get("user_id")
    if delete_user_account(user_id):
        session.clear()
        flash("✅ Your account has been deleted.", "success")
        return redirect(url_for("login"))
    else:
        flash("❌ Error deleting account.", "error")
        return redirect(url_for("profile"))

# ==================================================
# ✅ ANALYTICS (PERIOD FIXED)
# ==================================================
@app.route("/analytics")
@login_required
def analytics():
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    period = request.args.get("period", "day")  # default = day
    user_id = session.get("user_id")
    languages = get_language_stats(user_id)
    lengths_raw = get_length_stats(user_id)
    sentiments = get_sentiment_stats(user_id)
    activity = get_activity_stats(user_id)

    # ---- Map summary lengths ----
    length_map = {
        80: "Short",
        150: "Medium",
        250: "Long",
        "short": "Short",
        "medium": "Medium",
        "long": "Long",
        1: "Short",
        2: "Medium",
        3: "Long"
    }

    length_counts = {
    "Short": 0,
    "Medium": 0,
    "Long": 0
}

    for value, count in lengths_raw:
        value = int(value)
        if value == 80:
            length_counts["Short"] += count
        elif value == 150:
            length_counts["Medium"] += count
        elif value == 250:
            length_counts["Long"] += count

    len_labels = ["Short", "Medium", "Long"]
    len_counts = [
    length_counts["Short"],
    length_counts["Medium"],
    length_counts["Long"]
    ]

    # ---- Activity labels formatting based on period ----
    act_labels = []
    act_counts = []

    today = date.today()

    for day, count in activity:
        if period == "day":
            act_labels.append(str(day))
        elif period == "month":
            act_labels.append(f"Week {day}")
        else:  # year
            act_labels.append(f"Month {day}")

        act_counts.append(count)


    return render_template(
        "analytics.html",
        period=period,

        lang_labels=[l[0] for l in languages],
        lang_counts=[l[1] for l in languages],

        len_labels=len_labels,
        len_counts=len_counts,

        sent_labels=[s[0] or "Neutral" for s in sentiments],
        sent_counts=[s[1] for s in sentiments],

        act_labels=act_labels,
        act_counts=act_counts,

        avg_rating=get_average_rating(user_id),
    )
# ==================================================
# AUTOMATIC SCHEDULER (Daily at 9 AM, Weekly on Sunday 9 AM)
# ==================================================
scheduler = None

def start_scheduler():
    global scheduler
    if scheduler:
        return
    scheduler = BackgroundScheduler(daemon=True)
    # Daily Digest at 01:00 PM IST (07:30 UTC)
    scheduler.add_job(func=run_periodic_digest, args=['daily'], trigger="cron", hour=7, minute=30)
    # Weekly Digest on Sunday at 01:00 PM IST (07:30 UTC)
    scheduler.add_job(func=run_periodic_digest, args=['weekly'], trigger="cron", day_of_week='sun', hour=7, minute=30)
    
    scheduler.start()
    logger.info("⏰ Background Scheduler started successfully.")

    # 🚀 NEW: Catch-up Logic for missed digests on startup (e.g. if PC was off at 9 AM)
    from services.email_digest import was_digest_sent_today
    from datetime import datetime
    try:
        now = datetime.now()
        # ⚠️ NOTE: Server time is UTC. 01:00 PM IST = 07:30 AM UTC.
        # Catch-up triggers if started between 7:30 AM and midnight UTC.
        if now.hour > 7 or (now.hour == 7 and now.minute >= 30):
            if not was_digest_sent_today("daily"):
                logger.info("🕒 Startup check: Daily digest was missed at 01:00 PM IST. Triggering catch-up...")
                from threading import Thread
                Thread(target=run_periodic_digest, args=["daily"]).start()
    except Exception as e:
        logger.warning(f"Failed to check for missed digest on startup: {e}")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

# ==================================================
# ✅ EXTERNAL CRON TRIGGER (SECURITY TOKEN PROTECTED)
# ==================================================
@app.route("/api/cron/trigger", methods=["GET"])
def cron_trigger():
    """
    Endpoint for external wake-up services (like GitHub Actions or cron-job.org).
    Wakes up the HF Space and triggers the news update + email cycle.
    Usage: /api/cron/trigger?token=YOUR_CRON_SECRET
    """
    token = request.args.get("token")
    # Default fallback for local testing, but should be set in environment for production
    secret = os.environ.get("CRON_SECRET", "quicknews_123")
    
    if not token or token != secret:
        logger.warning(f"🚫 Unauthorized CRON trigger attempt from {request.remote_addr}")
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    logger.info("⚡ External CRON trigger received. Starting digest cycle...")
    from threading import Thread
    Thread(target=run_periodic_digest, args=["daily"]).start()
    
    return jsonify({
        "status": "success", 
        "message": "Daily digest cycle triggered successfully via cron."
    })

@app.route("/admin/trigger-auto-digest", methods=["POST"])
@login_required
@admin_required
def trigger_auto_digest():
    """Manual trigger for the periodic background task (updates news + sends)"""
    from threading import Thread
    Thread(target=run_periodic_digest, args=["daily"]).start()
    flash("🚀 Background digest cycle triggered manually (Updates news + Sends daily emails).", "info")
    return redirect(url_for("admin_panel"))

# ✅ AUTO-START SCHEDULER IN PRODUCTION (Gunicorn)
# On Hugging Face, gunicorn loads 'app'. We need the scheduler to start then.
# Locally, it starts when __name__ == "__main__" or when reloader is ready.
if __name__ == "app" or os.environ.get('GUNICORN_CMD_ARGS'):
    print("🚀 GUNICORN DETECTED - STARTING BACKGROUND TASKS...", flush=True)
    start_scheduler()

if __name__ == "__main__":
    logger.info("Starting QuickNewsAI application locally...")
    # Prevent double starting in Debug mode (Werkzeug reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        start_scheduler()
    app.run(debug=True, port=7860)  # Use port 7860 locally for better parity with HF
