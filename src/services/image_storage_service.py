"""
Lógica de almacenamiento de imágenes según su peso (punto 3 de la
especificación).

    peso <= 1 MB          -> MySQL, columna MEDIUMBLOB. Sin cifrar,
                              sin comprimir. Nada en MongoDB.
    1 MB < peso < 3 MB     -> archivo en /imagenes, cifrado AES-256GCM,
                              sin comprimir. Ruta + metadatos en MongoDB.
    peso >= 3 MB           -> archivo en /imagenes/comprimidas, cifrado
                              AES-256-GCM y comprimido. Ruta + metadatos
                              en MongoDB.

NOTA DE INTERPRETACIÓN (peso >= 3 MB):
La especificación original pide mostrar por defecto "la versión
comprimida" y, bajo demanda, "la imagen original descifrada y
descomprimida". Para que ambos casos entreguen una imagen realmente
visualizable en el navegador (y no bytes crudos de un compresor
genérico), se generan y cifran DOS archivos para este nivel:

  * <uuid>.enc           -> versión recomprimida con calidad reducida
                             (JPEG, Pillow) -- esta es la "vista por
                             defecto", rápida de cargar.
  * <uuid>.original.enc  -> bytes originales sin ninguna alteración,
                             solo cifrados -- esta es la "imagen
                             original" servida bajo demanda.

Ambos archivos están cifrados con AES-256-GCM y solo se descifran en
memoria al servirse por el endpoint protegido; nunca se escribe una
copia descifrada en disco. Si la intención original era otra (p. ej.
un único archivo con compresión sin pérdida reversible), este módulo
es el único punto que habría que ajustar.
"""
import io
import os
import uuid
from datetime import datetime, timezone

from PIL import Image

from src.config.settings import config
from src.services.crypto_service import cifrar_bytes, descifrar_bytes

CALIDAD_COMPRESION_JPEG = 60
LADO_MAXIMO_COMPRESION = 1600  # px, redimensiona si excede este lado mayor


def _asegurar_directorios():
    os.makedirs(config.IMAGENES_DIR, exist_ok=True)
    os.makedirs(config.IMAGENES_COMPRIMIDAS_DIR, exist_ok=True)


def clasificar_por_peso(tamano_bytes: int) -> str:
    if tamano_bytes <= config.UMBRAL_BLOB:
        return 'blob'
    if tamano_bytes < config.UMBRAL_COMPRESION:
        return 'cifrada'
    return 'comprimida'


def _comprimir_imagen(datos: bytes) -> bytes:
    """Recomprime la imagen a JPEG con calidad reducida. Si el formato no
    es soportado o falla la recompresión, cae en devolver los bytes
    originales (la imagen igual queda cifrada y funcional, solo sin
    reducción de peso)."""
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen = imagen.convert('RGB')
        lado_mayor = max(imagen.size)
        if lado_mayor > LADO_MAXIMO_COMPRESION:
            factor = LADO_MAXIMO_COMPRESION / lado_mayor
            nuevo_tamano = (int(imagen.width * factor), int(imagen.height * factor))
            imagen = imagen.resize(nuevo_tamano, Image.LANCZOS)
        salida = io.BytesIO()
        imagen.save(salida, format='JPEG', quality=CALIDAD_COMPRESION_JPEG, optimize=True)
        return salida.getvalue()
    except Exception:
        return datos


def guardar_imagen(datos: bytes, nombre_original: str, mime_original: str):
    """Procesa y guarda una imagen recién subida según su peso.

    Devuelve un dict con la información necesaria para persistir en
    MySQL y, si aplica, en MongoDB. No escribe nada en MySQL/Mongo aquí;
    eso es responsabilidad de los modelos que llaman a esta función.
    """
    tamano = len(datos)
    tipo = clasificar_por_peso(tamano)

    base = {
        'tipo': tipo,
        'tamano': tamano,
        'mime': mime_original,
        'nombre': nombre_original,
    }

    if tipo == 'blob':
        base['blob'] = datos
        return base

    _asegurar_directorios()
    identificador = uuid.uuid4().hex

    if tipo == 'cifrada':
        ruta = os.path.join(config.IMAGENES_DIR, f'{identificador}.enc')
        with open(ruta, 'wb') as f:
            f.write(cifrar_bytes(datos))
        base['ruta'] = ruta
        base['comprimida'] = False
        base['fecha_carga'] = datetime.now(timezone.utc)
        return base

    # tipo == 'comprimida'
    comprimida = _comprimir_imagen(datos)
    ruta_comprimida = os.path.join(config.IMAGENES_COMPRIMIDAS_DIR, f'{identificador}.enc')
    ruta_original = os.path.join(config.IMAGENES_COMPRIMIDAS_DIR, f'{identificador}.original.enc')
    with open(ruta_comprimida, 'wb') as f:
        f.write(cifrar_bytes(comprimida))
    with open(ruta_original, 'wb') as f:
        f.write(cifrar_bytes(datos))
    base['ruta'] = ruta_comprimida
    base['ruta_original'] = ruta_original
    base['comprimida'] = True
    base['fecha_carga'] = datetime.now(timezone.utc)
    return base


def leer_imagen_default(tipo: str, ruta: str) -> bytes:
    """Devuelve los bytes a mostrar por defecto (para 'comprimida' es la
    versión recomprimida, no la original). Descifra en memoria."""
    with open(ruta, 'rb') as f:
        return descifrar_bytes(f.read())


def leer_imagen_original(tipo: str, ruta: str, ruta_original: str = None) -> bytes:
    """Devuelve los bytes de la imagen original, descifrando bajo demanda
    sin dejar copias en disco."""
    if tipo == 'comprimida':
        with open(ruta_original, 'rb') as f:
            return descifrar_bytes(f.read())
    with open(ruta, 'rb') as f:
        return descifrar_bytes(f.read())


def eliminar_archivos(tipo: str, ruta: str = None, ruta_original: str = None):
    for path in (ruta, ruta_original):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
