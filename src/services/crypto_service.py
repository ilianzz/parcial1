"""
Cifrado simétrico de archivos con AES-256 en modo GCM.

GCM se eligió sobre CBC porque además de confidencialidad aporta
autenticación (detecta si el archivo cifrado fue alterado) y no requiere
padding manual. La clave nunca se hardcodea: se lee en base64 desde la
variable de entorno AES_KEY_BASE64 (ver src/config/settings.py).

Formato del archivo cifrado en disco:
    [12 bytes nonce] + [ciphertext] + [16 bytes tag]  (tag ya incluido
    por AESGCM.encrypt al final del ciphertext)
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.config.settings import config

NONCE_BYTES = 12


def _clave():
    clave = base64.b64decode(config.AES_KEY_BASE64)
    if len(clave) != 32:
        raise RuntimeError(
            'AES_KEY_BASE64 debe decodificar a exactamente 32 bytes (AES-256). '
            'Genera una nueva con: '
            'python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"'
        )
    return clave


def cifrar_bytes(datos: bytes) -> bytes:
    aesgcm = AESGCM(_clave())
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, datos, associated_data=None)
    return nonce + ciphertext


def descifrar_bytes(datos_cifrados: bytes) -> bytes:
    aesgcm = AESGCM(_clave())
    nonce, ciphertext = datos_cifrados[:NONCE_BYTES], datos_cifrados[NONCE_BYTES:]
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
