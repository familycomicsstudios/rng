from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import random
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
CORS(app, supports_credentials=True, origins=['*'])

DATABASE_URL = os.getenv('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                last_roll_time DOUBLE PRECISION DEFAULT NULL
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                rarity BIGINT NOT NULL,
                modifier TEXT DEFAULT NULL,
                count INTEGER DEFAULT 1,
                UNIQUE(user_id, rarity, modifier)
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()

# Initialize database on startup (important for serverless)
init_db()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        # Don't set last_roll_time - let it be NULL so first roll is always allowed
        cur.execute('INSERT INTO users (username, password) VALUES (%s, %s)', 
                   (username, hashed_password))
        conn.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'message': 'Login successful', 'username': username}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session['username']}), 200
    return jsonify({'logged_in': False}), 200

MODIFIERS = {
    'Developer': {'chance': 0.00001, 'multiplier': 100000, 'gradient': 'linear-gradient(135deg, #00ff00 0%, #ffff00 100%)'},
    'Negative': {'chance': 0.001, 'multiplier': 1000, 'gradient': 'linear-gradient(135deg, #000000 0%, #ffffff 100%)'},
    'Polychrome': {'chance': 0.01, 'multiplier': 100, 'gradient': 'linear-gradient(135deg, #ff0000 0%, #ff7f00 16%, #ffff00 33%, #00ff00 50%, #0000ff 66%, #4b0082 83%, #9400d3 100%)'},
    'Holographic': {'chance': 0.1, 'multiplier': 10, 'gradient': 'linear-gradient(135deg, #00ff00 0%, #00bfff 100%)'},
}

def calculate_modifier():
    """
    Roll for a modifier with decreasing probability.
    Returns (modifier_name, multiplier, gradient) or (None, 1, None)
    """
    roll = random.random()
    
    # Check modifiers from rarest to most common
    for modifier_name in ['Developer', 'Negative', 'Polychrome', 'Holographic']:
        modifier = MODIFIERS[modifier_name]
        if roll < modifier['chance']:
            return modifier_name, modifier['multiplier'], modifier['gradient']
    
    return None, 1, None

def calculate_rng_result():
    """
    Probabilistic RNG system:
    - 1 in 2 chance (50%) to get "1 in 2"
    - 1 in 3 chance (33.33%) to get "1 in 3"
    - 1 in 4 chance (25%) to get "1 in 4"
    - etc. infinitely
    
    We roll each rarity starting from 2, and the first one that succeeds is returned.
    """
    rarity = 2
    while True:
        roll = random.randint(1, rarity)
        if roll == 1:
            return rarity
        rarity += 1
        # Safety limit to prevent infinite loops (extremely rare to reach high numbers)
        if rarity > 1000000:
            return rarity

@app.route('/roll', methods=['POST'])
def roll():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    current_time = time.time()
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT last_roll_time FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        
        # Check cooldown (10 seconds)
        cooldown_seconds = 10
        last_roll = user['last_roll_time']
        
        # If last_roll is None or cooldown has passed, allow the roll
        # If last_roll is set, enforce cooldown with modulo to handle skew
        if last_roll is not None:
            time_since_last_roll = current_time - float(last_roll)
            # Only enforce when time has progressed; handle negative skew by allowing roll
            if time_since_last_roll >= 0 and time_since_last_roll < cooldown_seconds:
                # Modulo to cap remaining within [0, cooldown_seconds)
                remaining = (cooldown_seconds - time_since_last_roll) % cooldown_seconds
                return jsonify({'error': 'Cooldown active', 'remaining': remaining}), 429
            
        # Calculate RNG result
        base_rarity = calculate_rng_result()
        modifier_name, multiplier, gradient = calculate_modifier()
        true_rarity = base_rarity * multiplier
        
        # Update last roll time
        cur.execute('UPDATE users SET last_roll_time = %s WHERE id = %s', (current_time, user_id))
        
        # Add to inventory - handle NULL modifier comparison properly
        if modifier_name:
            cur.execute('SELECT * FROM inventory WHERE user_id = %s AND rarity = %s AND modifier = %s', 
                       (user_id, true_rarity, modifier_name))
            existing = cur.fetchone()
        else:
            cur.execute('SELECT * FROM inventory WHERE user_id = %s AND rarity = %s AND modifier IS NULL', 
                       (user_id, true_rarity))
            existing = cur.fetchone()
        
        if existing:
            if modifier_name:
                cur.execute('UPDATE inventory SET count = count + 1 WHERE user_id = %s AND rarity = %s AND modifier = %s',
                           (user_id, true_rarity, modifier_name))
            else:
                cur.execute('UPDATE inventory SET count = count + 1 WHERE user_id = %s AND rarity = %s AND modifier IS NULL',
                           (user_id, true_rarity))
        else:
            cur.execute('INSERT INTO inventory (user_id, rarity, modifier, count) VALUES (%s, %s, %s, 1)',
                       (user_id, true_rarity, modifier_name))
        
        conn.commit()
        
        return jsonify({
            'rarity': true_rarity,
            'modifier': modifier_name,
            'gradient': gradient,
            'message': f'You got a {modifier_name + " " if modifier_name else ""}1 in {true_rarity}!'
        }), 200
    finally:
        cur.close()
        conn.close()

@app.route('/inventory', methods=['GET'])
def get_inventory():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get inventory sorted by rarity (rarest first)
    cur.execute('''
        SELECT rarity, modifier, count FROM inventory 
        WHERE user_id = %s 
        ORDER BY rarity DESC
    ''', (user_id,))
    items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    inventory = []
    for item in items:
        modifier_data = None
        if item['modifier']:
            modifier_data = {
                'name': item['modifier'],
                'gradient': MODIFIERS[item['modifier']]['gradient']
            }
        inventory.append({
            'rarity': item['rarity'], 
            'modifier': modifier_data,
            'count': item['count']
        })
    
    # Get rarest item
    rarest_rarity = items[0]['rarity'] if items else 0
    
    return jsonify({'inventory': inventory, 'rarest': rarest_rarity}), 200

@app.route('/cooldown', methods=['GET'])
def get_cooldown():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    current_time = time.time()
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT last_roll_time FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    cooldown_seconds = 10
    last_roll = user['last_roll_time']
    
    # If last_roll is set, compute remaining with modulo and handle skew
    if last_roll is not None:
        time_since_last_roll = current_time - float(last_roll)
        # Only show cooldown when time has progressed; negative skew -> no cooldown
        if time_since_last_roll >= 0 and time_since_last_roll < cooldown_seconds:
            remaining = (cooldown_seconds - time_since_last_roll) % cooldown_seconds
            return jsonify({'on_cooldown': True, 'remaining': remaining}), 200
    
    return jsonify({'on_cooldown': False, 'remaining': 0}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
