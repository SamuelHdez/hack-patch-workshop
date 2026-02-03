# TicketNow - Entorno vulnerable para Hack & Patch

from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response, g
import json, os
import pickle
import sqlite3
import requests

app = Flask(__name__)
DATABASE = 'tebasaenterar.db'
# Variable de entorno para simular modo desarrollo/producción
ENV = os.environ.get('APP_ENV', 'dev')

sessions = {}
events = [
     {'id': 1, 'title': 'Concierto Bad Bunny 2025', 'image': 'https://via.placeholder.com/150'},
    {'id': 2, 'title': 'AC/DC', 'image': 'https://via.placeholder.com/150'},
    {'id': 3, 'title': 'Codemotion 2025', 'image': 'https://via.placeholder.com/150'}
]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    user = request.cookies.get('user')
    return render_template('index.html', user=user)

@app.route('/palancas')
def palancas():
    user = request.cookies.get('user')
    userid = request.cookies.get('userid')
    if not user or not userid:
        return redirect(url_for('login'))
    
    db = get_db()
    query = f"SELECT * FROM users WHERE id = {userid}"
    user_data = db.execute(query).fetchone()
    if not user_data:
        return redirect(url_for('login'))
    
    query = f"SELECT * FROM palancas WHERE user_id = {userid} ORDER BY id DESC"
    palanca_data = db.execute(query).fetchall()
    
    palancas_deserializadas = []
    for palanca in palanca_data:
        try:
            contenido_bytes = palanca['contenido'].encode('latin1')
            # Check if the content is valid for deserialization
            if contenido_bytes:
                contenido = pickle.loads(contenido_bytes)
                palancas_deserializadas.append(contenido)
            else:
                palancas_deserializadas.append({'error': 'Contenido vacío'})
        except Exception as e:
            palancas_deserializadas.append({'error': f'No se pudo deserializar: {str(e)}'})
    
    return render_template('palancas.html', user=user, balance=user_data['balance'], palancas=palancas_deserializadas)

@app.route('/checkout')
def checkout():
    user = request.cookies.get('user')
    userid = request.cookies.get('userid')
    item_id = request.args.get('id')
    
    if not item_id:
        return redirect(url_for('marketplace'))
    
    db = get_db()
    
    # Obtener datos del producto
    query = f"SELECT * FROM products WHERE id = {item_id}"
    
    try:
        item = db.execute(query).fetchone()
        if not item:
            return "Activo financiero no encontrado en el registro de Tebas.", 404
        
        # Obtener datos del usuario incluyendo balance
        balance = None
        if userid:
            user_query = f"SELECT balance FROM users WHERE id = {userid}"
            user_data = db.execute(user_query).fetchone()
            if user_data:
                balance = user_data['balance']
        
        return render_template('checkout.html', item=item, user=user, balance=balance)
    except Exception as e:
        return f"Error en la auditoría: {e}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    user_cookie = request.cookies.get('user')
    userid_cookie = request.cookies.get('user')
    if user_cookie:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        
        try:
            user = db.execute(query).fetchone()
            if user:
                resp = make_response(redirect(url_for('dashboard')))
                resp.set_cookie('user', user['username'])
                resp.set_cookie('userid', str(user['id']))
                return resp
            else:
                return 'Login incorrecto (Tebas no te deja pasar)'
        except Exception as e:
            return f"Error en la consulta: {e}<br>Query ejecutada: {query}"
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('user', '', expires=0)
    resp.set_cookie('userid', '', expires=0)
    return resp

@app.route('/dashboard')
def dashboard():
    user = request.cookies.get('user')
    if not user:
        return redirect(url_for('login'))
    avatars = load_avatars()
    avatar_url = avatars.get(user, '/static/default-avatar.png')
    return render_template('dashboard.html', user=user, avatar_url=avatar_url)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/marketplace')
def marketplace():
    user = request.cookies.get('user')
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY price DESC').fetchall()
    
    return render_template('marketplace.html', user=user, products=products)

AVATAR_FILE = 'avatars.json'

def load_avatars():
    if not os.path.exists(AVATAR_FILE):
        return {}
    with open(AVATAR_FILE, 'r') as f:
        return json.load(f)

def save_avatars(avatars):
    with open(AVATAR_FILE, 'w') as f:
        json.dump(avatars, f)

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    user = request.cookies.get('user')
    if request.method == 'POST':
        url = request.form['image_url']
        avatars = load_avatars()
        avatars[user] = url
        save_avatars(avatars)
        return redirect(url_for('dashboard'))
    return render_template('upload_image.html', user=user)

import pickle

@app.route('/cart')
def cart():
    user = request.cookies.get('user')
    return render_template('cart.html', user=user)

@app.route('/save_cart', methods=['POST'])
def save_cart():
    user = request.cookies.get('user')
    userid = request.cookies.get('userid')
    cart = request.form.get('cart')
    
    if not userid:
        return "Usuario no autenticado", 401
    
    try:
        # Convertir el JSON a objeto
        cart_obj = json.loads(cart)
        
        db = get_db()
        
        # Obtener datos del usuario
        user_query = f"SELECT balance FROM users WHERE id = {userid}"
        user_data = db.execute(user_query).fetchone()
        
        if not user_data:
            return "Usuario no encontrado", 404
        
        current_balance = user_data['balance']
        total_price = cart_obj.get('total_price', 0)
        
        if current_balance < total_price:
            return "Balance insuficiente", 400
        
        new_balance = current_balance - total_price
        update_query = f"UPDATE users SET balance = {new_balance} WHERE id = {userid}"
        db.execute(update_query)
        
        # Convertir el carrito a pickle y guardar
        cart_pickle = pickle.dumps(cart_obj).decode('latin1')
        
        insert_query = "INSERT INTO palancas (user_id, contenido) VALUES (?, ?)"
        db.execute(insert_query, (userid, cart_pickle))
        
        db.commit()
        return "Palanca aplicada correctamente"
    except Exception as e:
        print(e)
        return f"Error al guardar el carrito: {str(e)}", 500

@app.route('/load_cart')
def load_cart():
    try:
        with open('cart.pkl', 'rb') as f:
            cart = pickle.load(f)
        return f"{cart}"
    except Exception as e:
        print(e)
        return "Error al cargar carrito"
    
@app.route('/api/var-randomizer')
def var_randomizer():
    db = get_db()
    scandal = db.execute('SELECT * FROM var_scandals ORDER BY RANDOM() LIMIT 1').fetchone()
    return jsonify(dict(scandal))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/debug')
def debug():
    if ENV == 'prod':
        return "No disponible en producción"
    return jsonify({'debug': 'vars', 'env': ENV})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

