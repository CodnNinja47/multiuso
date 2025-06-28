from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tu_script

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

@app.route('/')
def index():
    return "API Multiuso Activa"

@app.route('/buscar', methods=['POST'])
def buscar_usuario():
    data = request.get_json()
    usuario = data.get("usuario")
    resultado = tu_script.buscar(usuario)
    return jsonify(resultado)

@app.route('/ip', methods=['POST'])
def buscar_ip():
    data = request.get_json()
    ip = data.get("ip")
    resultado = tu_script.buscar_ip(ip)
    return jsonify(resultado)

@app.route('/telefono', methods=['POST'])
def buscar_numero():
    data = request.get_json()
    numero = data.get("numero")
    resultado = tu_script.buscar_numero(numero)
    return jsonify(resultado)

# Configuración para Railway y Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Railway o Render usarán esta variable
    app.run(host='0.0.0.0', port=port)
