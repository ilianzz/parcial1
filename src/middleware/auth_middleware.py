from functools import wraps
from flask import request, jsonify, g
from src.services.auth_service import verificar_token


def jwt_required(f):
    """Exige un header 'Authorization: Bearer <token>' válido.
    Deja el id del usuario autenticado en g.usuario_id para que la vista
    lo use al filtrar/validar propiedad de los registros."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Falta el token de autenticación (Authorization: Bearer <token>).'}), 401
        token = auth_header.split(' ', 1)[1].strip()
        usuario_id = verificar_token(token)
        if usuario_id is None:
            return jsonify({'error': 'Token inválido o expirado. Inicia sesión nuevamente.'}), 401
        g.usuario_id = usuario_id
        return f(*args, **kwargs)
    return wrapper
