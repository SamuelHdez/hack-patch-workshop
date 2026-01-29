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

# Base de datos en memoria

sessions = {}
events = [
     {'id': 1, 'title': 'Concierto Bad Bunny 2025', 'image': 'https://via.placeholder.com/150'},
    {'id': 2, 'title': 'AC/DC', 'image': 'https://via.placeholder.com/150'},
    {'id': 3, 'title': 'Codemotion 2025', 'image': 'https://via.placeholder.com/150'}
]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        # Conectamos a la base de datos que creaste manualmente
        db = g._database = sqlite3.connect(DATABASE)
        # Esto permite acceder a las columnas por nombre: user['username'] en vez de user[1]
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

@app.route('/checkout')
def checkout():
    user = request.cookies.get('user')
    item_id = request.args.get('id')
    
    if not item_id:
        return redirect(url_for('marketplace'))
    
    db = get_db()
    # VULNERABILIDAD SQLi: Ideal para el workshop. 
    # Un ID malicioso podría saltarse filtros o extraer datos.
    query = f"SELECT * FROM products WHERE id = {item_id}"
    
    try:
        item = db.execute(query).fetchone()
        if not item:
            return "Activo financiero no encontrado en el registro de Tebas.", 404
            
        return render_template('checkout.html', item=item, user=user)
    except Exception as e:
        return f"Error en la auditoría: {e}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    user_cookie = request.cookies.get('user')
    if user_cookie:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        
        # VULNERABILIDAD CRÍTICA: SQL Injection
        # Usamos f-strings para que el input del usuario vaya directo a la query
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        
        try:
            user = db.execute(query).fetchone()
            if user:
                resp = make_response(redirect(url_for('dashboard')))
                resp.set_cookie('user', user['username'])
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
    # Este endpoint no debería estar accesible en producción
    return render_template('admin.html')

@app.route('/marketplace')
def marketplace():
    user = request.cookies.get('user')
    db = get_db()
    
    # Traemos todos los productos ordenados por precio (de más caro a menos caro)
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
    cart = request.form.get('cart')
    try:
        cart_data = eval(cart)  # Convert string representation to a Python object
        with open('cart.pkl', 'wb') as f:
            pickle.dump(cart_data, f)
        return "Carrito guardado"
    except Exception as e:
        print(e)
        return "Error al guardar el carrito"

@app.route('/load_cart')
def load_cart():
    try:
        with open('cart.pkl', 'rb') as f:
            cart = pickle.load(f)  # Insecure deserialization
        return f"{cart}"
    except Exception as e:
        print(e)
        return "Error al cargar carrito"

@app.route('/debug')
def debug():
    if ENV == 'prod':
        return "No disponible en producción"
    return jsonify({'debug': 'vars', 'env': ENV})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

