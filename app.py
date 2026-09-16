from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import sqlite3
import datetime
import urllib.request
import urllib.error
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'acew_secret_key_hackathon_2026')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = '/tmp/acew.db' if os.environ.get('VERCEL') else os.path.join(BASE_DIR, 'database.db')

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Announcements Table
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    category TEXT,
                    msg TEXT,
                    created_at TEXT
                )''')
                
    # Outpass Table
    c.execute('''CREATE TABLE IF NOT EXISTS outpasses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pass_id TEXT,
                    name TEXT,
                    dept TEXT,
                    reason TEXT,
                    status TEXT,
                    created_at TEXT
                )''')
                
    # Slot Bookings Table
    c.execute('''CREATE TABLE IF NOT EXISTS slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT,
                    regno TEXT,
                    purpose TEXT,
                    timeslot TEXT,
                    status TEXT
                )''')

    # Food Orders Table
    c.execute('''CREATE TABLE IF NOT EXISTS food_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    items TEXT,
                    status TEXT
                )''')

    # Marketplace Table
    c.execute('''CREATE TABLE IF NOT EXISTS marketplace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    category TEXT,
                    item_type TEXT,
                    price TEXT,
                    seller TEXT,
                    image_url TEXT
                )''')
    columns = [row[1] for row in c.execute("PRAGMA table_info(marketplace)").fetchall()]
    if 'image_url' not in columns:
        c.execute("ALTER TABLE marketplace ADD COLUMN image_url TEXT")

    # Seed Default Announcement if empty
    c.execute("SELECT COUNT(*) FROM announcements")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO announcements (title, category, msg, created_at) VALUES (?, ?, ?, ?)",
                  ("SIH Hackathon Internal Trials", "Academic", "Register your team at the AI Lab by Friday.", "Today"))
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- HTML Page Routes ---

@app.route('/')
def home():
    if not session.get('is_student') and not session.get('is_admin') and not session.get('is_guest'):
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    if session.get('is_student') or session.get('is_admin') or session.get('is_guest'):
        return redirect(url_for('home'))
    return render_template('login.html', error=request.args.get('error', ''))

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('admin.html')

@app.route('/admin-login', methods=['POST'])
def admin_login_form():
    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    if username == 'admin' and password == 'admin123':
        session['is_admin'] = True
        session.pop('is_student', None)
        session.pop('is_guest', None)
        return redirect(url_for('admin_page'))
    return redirect(url_for('login_page', error='Invalid username or password.'))

@app.route('/shuttle')
def shuttle(): return render_template('shuttle.html')

@app.route('/virtual')
def virtual(): return render_template('virtual.html')

@app.route('/wheelchair')
def wheelchair(): return render_template('wheelchair.html')

@app.route('/bus')
def bus(): return render_template('bus.html')

@app.route('/outpass')
def outpass(): return render_template('outpass.html')

@app.route('/sos')
def sos(): return render_template('sos.html')

@app.route('/slot')
def slot(): return render_template('slot.html')

@app.route('/food')
def food(): return render_template('food.html')

@app.route('/announce')
def announce(): return render_template('announce.html')

@app.route('/attendance')
def attendance(): return render_template('attendance.html')

@app.route('/ai-notes')
def ai_notes(): return render_template('ai_notes.html')

@app.route('/marketplace')
def marketplace(): return render_template('marketplace.html')

# --- Admin Authentication APIs ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    # Default Admin Credentials
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['is_admin'] = True
        session.pop('is_student', None)
        session.pop('is_guest', None)
        return jsonify({"status": "success", "message": "Admin login successful!"})
    return jsonify({"status": "error", "message": "Invalid Credentials!"}), 401

@app.route('/api/student-login', methods=['POST'])
def student_login():
    session['is_student'] = True
    session.pop('is_admin', None)
    session.pop('is_guest', None)
    if not request.is_json:
        return redirect(url_for('home'))
    return jsonify({"status": "success", "message": "Student login successful!"})

@app.route('/api/guest-login', methods=['POST'])
def guest_login():
    session['is_guest'] = True
    session.pop('is_student', None)
    session.pop('is_admin', None)
    if not request.is_json:
        return redirect(url_for('home'))
    return jsonify({"status": "success", "message": "Guest access enabled!"})

@app.route('/api/logout', methods=['GET'])
def logout():
    session.pop('is_admin', None)
    session.pop('is_student', None)
    session.pop('is_guest', None)
    return jsonify({"status": "success", "message": "Logged out!"})

# --- Announcements DB APIs ---

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]})

@app.route('/api/announcements/add', methods=['POST'])
def add_announcement():
    if not session.get('is_admin'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    data = request.get_json(silent=True) or {}
    now = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    conn = get_db_connection()
    conn.execute("INSERT INTO announcements (title, category, msg, created_at) VALUES (?, ?, ?, ?)",
                 (data['title'], data['category'], data['msg'], now))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Announcement posted to Database!"})

# --- Outpass DB APIs ---

@app.route('/api/outpass/apply', methods=['POST'])
def apply_outpass():
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM outpasses").fetchone()[0]
    pass_id = f"ACEW-2026-00{count + 1}"
    now = datetime.datetime.now().strftime("%d %b %Y")
    
    conn.execute("INSERT INTO outpasses (pass_id, name, dept, reason, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (pass_id, data['name'], data['dept'], data['reason'], 'Approved by Warden', now))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "outpass_id": pass_id})

@app.route('/api/outpass/list', methods=['GET'])
def get_outpasses():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM outpasses ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]})

# --- Cash Slot Booking DB APIs ---

@app.route('/api/book-slot', methods=['POST'])
def book_slot():
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0]
    token = f"SLOT-AC-{count + 101}"
    
    conn.execute("INSERT INTO slots (token, regno, purpose, timeslot, status) VALUES (?, ?, ?, ?, ?)",
                 (token, data['regno'], data['purpose'], data['timeslot'], 'Confirmed'))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Token Generated: {token}", "token": token})

@app.route('/api/slots/list', methods=['GET'])
def get_slots():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM slots ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]})

# --- Food Orders DB APIs ---

@app.route('/api/food/order', methods=['POST'])
def food_order():
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM food_orders").fetchone()[0]
    order_id = f"FOOD-{count + 501}"
    items_str = ", ".join(data.get('items', []))
    
    conn.execute("INSERT INTO food_orders (order_id, items, status) VALUES (?, ?, ?)",
                 (order_id, items_str, 'Preparing'))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "order_id": order_id})

@app.route('/api/food/list', methods=['GET'])
def get_food_orders():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM food_orders ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]})

# --- Marketplace DB APIs ---

@app.route('/api/marketplace/list', methods=['GET'])
def get_marketplace():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM marketplace ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]})

@app.route('/api/marketplace/add', methods=['POST'])
def add_marketplace():
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    item_type = data.get('item_type') or data.get('type') or 'Sell'
    conn.execute("INSERT INTO marketplace (title, category, item_type, price, seller, image_url) VALUES (?, ?, ?, ?, ?, ?)",
                 (data['title'], data['category'], item_type, data['price'], data['seller'], data.get('image_url', '')))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Listing published!"})

# --- Academic Bot powered by Gemini ---
@app.route('/api/academic-chat', methods=['POST'])
def academic_chat():
    # User must be logged in.
    if not session.get('is_student') and not session.get('is_admin') and not session.get('is_guest'):
        return jsonify({
            "status": "error",
            "message": "Please login first to use the AI tutor."
        }), 401

    data = request.get_json(silent=True) or {}
    question = str(data.get('question') or '').strip()

    if not question:
        return jsonify({
            "status": "error",
            "message": "Please enter a question."
        }), 400

    if len(question) > 4000:
        return jsonify({
            "status": "error",
            "message": "Please keep your question under 4000 characters."
        }), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({
            "status": "error",
            "message": "GEMINI_API_KEY is not configured. Add it to your .env file."
        }), 503

    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    context = data.get('context')
    if not isinstance(context, dict):
        context = {}

    system_prompt = (
        "You are ACEW Student Hub AI Tutor. "
        "Help college students with studies, programming, engineering concepts, "
        "assignments, projects, careers, interviews, internships, and technical skills. "
        "Explain step by step in simple beginner-friendly language. "
        "For programming questions, provide working code and explain it. "
        "Do not claim to access private college records. "
        f"Selected subject: {context.get('subject', 'general')}. "
        f"Selected unit: {context.get('unit', 'general')}. "
        f"Selected topic: {context.get('topic', 'general')}."
    )

    history = data.get('history')
    if not isinstance(history, list):
        history = []

    messages = [{"role": "system", "content": system_prompt}]

    for item in history[-8:]:
        if (
            isinstance(item, dict)
            and item.get('role') in ('user', 'assistant')
            and item.get('content')
        ):
            messages.append({
                "role": item['role'],
                "content": str(item['content'])[:4000]
            })

    messages.append({
        "role": "user",
        "content": question
    })

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    gemini_payload = json.dumps({
        "contents": [{
            "parts": [{"text": "\n".join(item["content"] for item in messages if isinstance(item, dict) and "content" in item)}]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 600
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        gemini_url,
        data=gemini_payload,
        method="POST",
        headers={
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates") or []
        if not candidates:
            return jsonify({
                "status": "error",
                "message": "Gemini returned no candidates."
            }), 502

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        answer = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()

        if not answer:
            return jsonify({
                "status": "error",
                "message": "Gemini returned an empty answer."
            }), 502

        return jsonify({
            "status": "success",
            "answer": answer
        })

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        return jsonify({
            "status": "error",
            "message": f"Gemini API error ({error.code}): {details}"
        }), error.code

    except urllib.error.URLError as error:
        return jsonify({
            "status": "error",
            "message": f"Cannot connect to Gemini: {error.reason}"
        }), 502

    except json.JSONDecodeError:
        return jsonify({
            "status": "error",
            "message": "Gemini returned invalid JSON."
        }), 502

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(error)}"
        }), 500


@app.route('/api/academic-notes', methods=['POST'])
def academic_notes():
    data = request.get_json(silent=True) or {}

    # Prefer the server-side key. Accepting a client key is retained for compatibility
    # with the existing frontend, but server-side .env is recommended.
    api_key = os.environ.get('GEMINI_API_KEY') or data.get('api_key')

    if not api_key:
        return jsonify({
            "status": "error",
            "message": "Gemini API Key is required."
        }), 400

    prompt = (
        "Provide detailed engineering study notes for college students.\n"
        f"Subject: {data.get('subject', 'General')}\n"
        f"Unit: {data.get('unit', 'General')}\n"
        f"Topic: {data.get('topic', 'General')}\n"
        "Include key concepts, simple explanations, examples, and bullet points."
    )

    model_name = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    gemini_payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 1600
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        gemini_url,
        data=gemini_payload,
        method="POST",
        headers={
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates") or []
        if not candidates:
            return jsonify({
                "status": "error",
                "message": "Gemini returned no candidates."
            }), 502

        notes = "".join(
            part.get("text", "")
            for part in ((candidates[0].get("content") or {}).get("parts") or [])
            if isinstance(part, dict)
        ).strip()

        if not notes:
            return jsonify({
                "status": "error",
                "message": "Gemini returned empty notes."
            }), 502

        return jsonify({
            "status": "success",
            "notes": notes
        })

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        return jsonify({
            "status": "error",
            "message": f"Gemini API error ({error.code}): {details}"
        }), error.code

    except urllib.error.URLError as error:
        return jsonify({
            "status": "error",
            "message": f"Cannot connect to Gemini: {error.reason}"
        }), 502

    except json.JSONDecodeError:
        return jsonify({
            "status": "error",
            "message": "Gemini returned invalid JSON."
        }), 502

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(error)}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "success",
        "message": "ACEW Student Hub backend is running.",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY"))
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)