import datetime
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from src.config.settings import config


def hashear_password(password: str) -> str:
    return generate_password_hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def generar_token(usuario_id: int) -> str:
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'sub': usuario_id,
        'iat': ahora,
        'exp': ahora + datetime.timedelta(hours=config.JWT_EXP_HORAS),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def verificar_token(token: str):
    """Devuelve el usuario_id si el token es válido, o None si no lo es
    (expirado, firma inválida, malformado, etc.)."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        return int(payload['sub'])
    except jwt.PyJWTError:
        return None
