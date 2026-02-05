# TicketNow - Entorno vulnerable para Hack & Patch

from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response, g
import json, os
import pickle
import sqlite3
import requests
import base64
from urllib.request import urlopen

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

@app.before_request
def block_external_internal_routes():
    if (request.path.startswith('/readfile') or request.path.startswith('/admin')) and request.remote_addr != '127.0.0.1' and request.remote_addr != 'localhost':
        return "403 Forbidden, Internal Only.", 403
    
@app.route('/readfile')
def internal_lfi():
    filepath = request.args.get('file')
    print(f"[DEBUG] Intentando abrir: {filepath}")
    if not filepath:
        return "❌ Falta el parámetro `file`", 400
 
    # Limitar el acceso a la carpeta static
    print(f"[DEBUG] 1")
 
    if not os.path.isfile(filepath):
        return f"❌ Archivo no encontrado: {filepath}", 404
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
 
        # Limitar el tamaño para evitar respuestas enormes
        return requests.Response(content, mimetype='text/plain')
    except Exception as e:
        return f"❌ Error leyendo el archivo: {e}", 500       

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
            contenido_bytes = palanca['contenido']
            if contenido_bytes:
                contenido = pickle.loads(contenido_bytes)
                palancas_deserializadas.append(contenido)
            else:
                palancas_deserializadas.append({'error': 'Contenido vacío'})
        except Exception as e:
            print(f"[ERROR] Error en deserialización: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
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
        
        return render_template('checkout.html', item=item, user=user, userid=userid, balance=balance)
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
    userid = request.cookies.get('userid')
    if not user:
        return redirect(url_for('login'))
    db = get_db()
    query = f"SELECT * FROM users WHERE id = {userid}"
    user_data = db.execute(query).fetchone()
    if not user_data:
        return redirect(url_for('login'))
    avatar_url = user_data['avatar']
    try:
        response = requests.get(avatar_url, timeout=2, verify=False)
        encoded = base64.b64encode(response.content).decode()
        data_url = f"data:image/jpeg;base64,{encoded}"
        print(f"[DEBUG] Avatar descargado: {avatar_url[:60]}")
    except Exception as e:
        print(f"[SSRF] Falló la petición: {e}")
    return render_template('dashboard.html', user=user, avatar_url=data_url)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/marketplace')
def marketplace():
    user = request.cookies.get('user')
    db = get_db()
    products = db.execute('SELECT * FROM products ORDER BY price DESC').fetchall()
    
    return render_template('marketplace.html', user=user, products=products)

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    user = request.cookies.get('user')
    userid = request.cookies.get('userid')
    if request.method == 'POST':
        url = request.form['image_url']
        db = get_db()
        query = f"UPDATE users SET avatar = '{url}' WHERE id = {userid}"
        try:
            db.execute(query)
            db.commit()
        except Exception as e:
            return f"Error al actualizar el avatar: {e}<br>Query ejecutada: {query}"        
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
    encoded = request.form.get('cart')
    decoded = base64.b64decode(encoded)
    if not userid:
        return "Usuario no autenticado", 401
    
    try:
        db = get_db()
        
        # Obtener datos del usuario
        user_query = f"SELECT balance FROM users WHERE id = {userid}"
        user_data = db.execute(user_query).fetchone()
        
        if not user_data:
            return "Usuario no encontrado", 404
        
        # Convertir el carrito a pickle y guardar
        decoded_text = decoded.decode('utf-8', errors='ignore')
        cart_data = json.loads(decoded_text)
        cart_pickle = pickle.dumps(cart_data)
        
        insert_query = "INSERT INTO palancas (user_id, contenido) VALUES (?, ?)"
        db.execute(insert_query, (userid, cart_pickle))
        
        db.commit()

        cart_obj = json.loads(decoded_text)
        current_balance = user_data['balance']
        total_price = cart_obj.get('total_price', 0)
        
        if current_balance < total_price:
            return "Balance insuficiente", 400
        
        new_balance = current_balance - total_price
        update_query = f"UPDATE users SET balance = {new_balance} WHERE id = {userid}"
        db.execute(update_query)
        db.commit()
         
        return "Palanca aplicada correctamente"
    except (UnicodeDecodeError, json.JSONDecodeError):
        db = get_db()
        
        # Obtener datos del usuario
        user_query = f"SELECT balance FROM users WHERE id = {userid}"
        user_data = db.execute(user_query).fetchone()
        
        if not user_data:
            return "Usuario no encontrado", 404
        
        insert_query = "INSERT INTO palancas (user_id, contenido) VALUES (?, ?)"
        db.execute(insert_query, (userid, decoded))
        
        db.commit()
        return "Palanca aplicada correctamente (con contenido no JSON)"
    except Exception as e:
        print(f"[ERROR] Exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error al guardar el carrito: {str(e)}", 500
    
@app.route('/api/var-randomizer')
def var_randomizer():
    db = get_db()
    scandal = db.execute('SELECT * FROM var_scandals ORDER BY RANDOM() LIMIT 1').fetchone()
    return jsonify(dict(scandal))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/logs')
def logs():
    with open('logs.txt', 'rb') as f:
        return f.read()

@app.route('/debug')
def debug():
    if ENV == 'prod':
        return "No disponible en producción"
    return jsonify({'debug': 'vars', 'env': ENV,'useradmin':'tebas','adminpass':'4qu3d4rs1n1nt3rn3tcu4nd0h4yp4rt1d0', 'status':'Eres un chafardero, no deberias ver esto...','category':'golismeador'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

