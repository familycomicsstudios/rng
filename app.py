from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
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

# Detect if running on Vercel
IS_VERCEL = os.getenv('VERCEL') == '1'
DATABASE_URL = os.getenv('POSTGRES_URL')

if IS_VERCEL and DATABASE_URL:
    USE_POSTGRES = True
else:
    USE_POSTGRES = False
    DATAcursor = db.cursor()
        
        if USE_POSTGRES:
            # PostgreSQL syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    last_roll_time DOUBLE PRECISION DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    rarity BIGINT NOT NULL,
                    modifier TEXT DEFAULT NULL,
                    count INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, rarity, modifier)
                )
            ''')
        else:
            # SQLite syntax
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    last_roll_time REAL DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rarity INTEGER NOT NULL,
                    modifier TEXT DEFAULT NULL,
                    count INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, rarity, modifier)
                )
            ''')
            
            # Migration: Add modifier column to existing inventory table if it doesn't exist (SQLite only)
            try:
                cursor.execute('SELECT modifier FROM inventory LIMIT 1')
            except sqlite3.OperationalError:
                cursor.execute('ALTER TABLE inventory ADD COLUMN modifier TEXT DEFAULT NULL')
        
        db.commit()
        cursor.close
        # Migration: Add modifier column to existing inventory table if it doesn't exist
        try:
            db.execute('SELECT modifier FROM inventory LIMIT 1')
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            db.execute('ALTER TABLE inventory ADD COLUMN modifier TEXT DEFAULT NULL')
            # Drop old unique constraint and recreate with modifier
            db.execute('DROP INDEX IF EXISTS sqlite_autoindex_inventory_1')
            # SQLite doesn't allow dropping constraints, so we need to recreate the table
            db.execute('CREATE TABLE inventory_new (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, rarity INTEGER NOT NULL, modifier TEXT DEFAULT NULL, count INTEGER DEFAULT 1, FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, rarity, modifier))')
            db.execute('INSERT INTO inventory_new (id, user_id, rarity, count, modifier) SELECT id, user_id, rarity, count, NULL FROM inventory')
            db.execute('DROP TABLE inventory')
            db.execute('ALTER TABLE inventory_new RENAME TO inventory')
        
        db.commit()
cursor = db.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)' if USE_POSTGRES else 'INSERT INTO users (username, password) VALUES (?, ?)', 
                   (username, hashed_password))
        db.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        cursor.close()/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    db = get_db()
    try:
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s' if USE_POSTGRES else 'SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    cursor.clos
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                   (username, hashed_password))
        db.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        db.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    db.close()
    
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
    
    db = get_db()
    cursor = db.cursor()
    try:
        param = '%s' if USE_POSTGRES else '?'
        cursor.execute(f'SELECT last_roll_time FROM users WHERE id = {param}', (user_id,))
        user = cursor.fetchone()
        
        # Check cooldown (10 seconds)
        cooldown_seconds = 10
        time_since_last_roll = current_time - user['last_roll_time']
        
        if time_since_last_roll < cooldown_seconds:
            remaining = cooldown_seconds - time_since_last_roll
            return jsonify({'error': 'Cooldown active', 'remaining': remaining}), 429
        
        # Calculate RNG result
        base_rarity = calculate_rng_result()
        modifier_name, multiplier, gradient = calculate_modifier()
        true_rarity = base_rarity * multiplier
        
        # Update last roll time
        cursor.execute(f'UPDATE users SET last_roll_time = {param} WHERE id = {param}', (current_time, user_id))
        
        # Add to inventory - handle NULL modifier comparison properly
        if modifier_name:
            cursor.execute(f'SELECT * FROM inventory WHERE user_id = {param} AND rarity = {param} AND modifier = {param}', 
                          (user_id, true_rarity, modifier_name))
        else:
            cursor.execute(f'SELECT * FROM inventory WHERE user_id = {param} AND rarity = {param} AND modifier IS NULL', 
                          (user_id, true_rarity))
        existing = cursor.fetchone()
        
        if existing:
            if modifier_name:
                cursor.execute(f'UPDATE inventory SET count = count + 1 WHERE user_id = {param} AND rarity = {param} AND modifier = {param}',
                           (user_id, true_rarity, modifier_name))
            else:
                cursor.execute(f'UPDATE inventory SET count = count + 1 WHERE user_id = {param} AND rarity = {param} AND modifier IS NULL',
                           (user_id, true_rarity))
        else:
            cursor.execute(f'INSERT INTO inventory (user_id, rarity, modifier, count) VALUES ({param}, {param}, {param}, 1)',
                       (user_id, true_rarity, modifier_name))
        
        db.commit()
        
        return jsonify({
            'rarity': true_rarity,
            'modifier': modifier_name,
            'gradient': gradient,
            'message': f'You got a {modifier_name + " " if modifier_name else ""}1 in {true_rarity}!'
        }), 200
    finally:
        cursor.close()
        db.close()

@app.route('/inventory', methods=['GET'])
def get_inventory():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    
    param = '%s' if USE_POSTGRES else '?'
    # Get inventory sorted by rarity (rarest first)
    cursor.execute(f'''
        SELECT rarity, modifier, count FROM inventory 
        WHERE user_id = {param}
        ORDER BY rarity DESC
    ''', (user_id,))
    items = cursor.fetchall()
    
    cursor.close()
    db.close()
    
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
    
    cursor = db.cursor()
    param = '%s' if USE_POSTGRES else '?'
    cursor.execute(f'SELECT last_roll_time FROM users WHERE id = {param}', (user_id,))
    user = cursor.fetchone()
    cursor.clos
    current_time = time.time()
    
    db = get_db()
    user = db.execute('SELECT last_roll_time FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    
    cooldown_seconds = 10
    time_since_last_roll = current_time - user['last_roll_time']
    
    if time_since_last_roll < cooldown_seconds:
        remaining = cooldown_seconds - time_since_last_roll
        return jsonify({'on_cooldown': True, 'remaining': remaining}), 200
    
    return jsonify({'on_cooldown': False, 'remaining': 0}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
