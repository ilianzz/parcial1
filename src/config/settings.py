"""
Configuración centralizada. Todo se lee de variables de entorno (.env en
desarrollo). Nunca se hardcodean credenciales ni claves de cifrado aquí.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(nombre, default=None, permitir_vacio=False):
    valor = os.getenv(nombre, default)
    if valor is None and not permitir_vacio:
        raise RuntimeError(
            f'Falta la variable de entorno obligatoria "{nombre}". '
            f'Define un archivo .env (ver .env.example).'
        )
    return valor


class Config:
    # --- Flask / JWT ---
    SECRET_KEY = _require('SECRET_KEY')
    JWT_ALGORITHM = 'HS256'
    JWT_EXP_HORAS = int(os.getenv('JWT_EXP_HORAS', '24'))

    # --- MySQL ---
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = _require('MYSQL_PASSWORD', permitir_vacio=True)
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'mercancia')

    # --- MongoDB ---
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'mercancia')

    # --- Cifrado de imágenes (AES-256-GCM) ---
    # Debe ser una clave de 32 bytes codificada en base64. Generar con:
    #   python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
    AES_KEY_BASE64 = _require('AES_KEY_BASE64')

    # --- Almacenamiento de imágenes en disco ---
    IMAGENES_DIR = os.getenv('IMAGENES_DIR', os.path.join(os.getcwd(), 'imagenes'))
    IMAGENES_COMPRIMIDAS_DIR = os.path.join(IMAGENES_DIR, 'comprimidas')

    # --- Umbrales de la tabla de la especificación (en bytes) ---
    UMBRAL_BLOB = 1 * 1024 * 1024        # <= 1 MB -> MySQL MEDIUMBLOB
    UMBRAL_COMPRESION = 3 * 1024 * 1024  # >= 3 MB -> cifrada + comprimida

    # Límite absoluto de subida (protección adicional; ajustar si se
    # necesitan imágenes más grandes).
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024

    MIME_PERMITIDOS = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    }


config = Config()
