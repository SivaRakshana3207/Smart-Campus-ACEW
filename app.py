from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import sqlite3
import datetime
import urllib.request
import json
import os

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
                    seller TEXT
                )''')

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
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('admin.html')

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
    data = request.json
    # Default Admin Credentials
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['is_admin'] = True
        return jsonify({"status": "success", "message": "Admin login successful!"})
    return jsonify({"status": "error", "message": "Invalid Credentials!"}), 401

@app.route('/api/logout', methods=['GET'])
def logout():
    session.pop('is_admin', None)
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
    
    data = request.json
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
    data = request.json
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
    data = request.json
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
    data = request.json
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
    data = request.json
    conn = get_db_connection()
    conn.execute("INSERT INTO marketplace (title, category, item_type, price, seller) VALUES (?, ?, ?, ?, ?)",
                 (data['title'], data['category'], data['item_type'], data['price'], data['seller']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Listing published!"})

# --- Groq AI Proxy Endpoint ---

@app.route('/api/groq-generate', methods=['POST'])
def groq_generate():
    data = request.json
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({"status": "error", "message": "Groq API Key is required"}), 400

    prompt = f"Provide detailed engineering study notes for 3rd Year students.\nSubject: {data.get('subject')}\nUnit: {data.get('unit')}\nTopic: {data.get('topic')}\nInclude key concepts and bullet points."

    payload = json.dumps({
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            return jsonify({"status": "success", "notes": res_data['choices'][0]['message']['content']})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)