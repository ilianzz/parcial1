import re
from flask import Blueprint, request, jsonify
from src.models.model_usuario import Usuario
from src.services.auth_service import hashear_password, verificar_password, generar_token

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

CORREO_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@auth_bp.route('/registro', methods=['POST'])
def registro():
    datos = request.get_json(silent=True) or {}
    nombre = (datos.get('nombre') or '').strip()
    correo = (datos.get('correo') or '').strip().lower()
    password = datos.get('password') or ''

    if not nombre or not correo or not password:
        return jsonify({'error': 'nombre, correo y password son obligatorios.'}), 400
    if not CORREO_REGEX.match(correo):
        return jsonify({'error': 'El correo no tiene un formato válido.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres.'}), 400
    if Usuario.buscar_por_correo(correo):
        return jsonify({'error': 'Ya existe una cuenta con ese correo.'}), 409

    usuario_id = Usuario.crear(nombre, correo, hashear_password(password))
    token = generar_token(usuario_id)
    return jsonify({'token': token, 'usuario': {'id': usuario_id, 'nombre': nombre, 'correo': correo}}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    datos = request.get_json(silent=True) or {}
    correo = (datos.get('correo') or '').strip().lower()
    password = datos.get('password') or ''

    usuario = Usuario.buscar_por_correo(correo)
    if not usuario or not verificar_password(password, usuario['password_hash']):
        # Mensaje genérico a propósito: no revelar si el correo existe.
        return jsonify({'error': 'Correo o contraseña incorrectos.'}), 401

    token = generar_token(usuario['idusuario'])
    return jsonify({
        'token': token,
        'usuario': {'id': usuario['idusuario'], 'nombre': usuario['nombre'], 'correo': usuario['correo']},
    }), 200
