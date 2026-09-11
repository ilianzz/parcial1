"""
Orquesta la creación/edición/eliminación de un producto junto con su
imagen, que puede terminar en MySQL (BLOB), en disco cifrado (con
metadatos en Mongo) o no existir. Si algo falla a mitad de camino, se
intenta deshacer lo ya hecho (archivos escritos, documento Mongo) para
no dejar residuos huérfanos.
"""
from src.models.model_producto import Producto
from src.models.model_imagen_meta import ImagenMeta
from src.services.image_storage_service import guardar_imagen, eliminar_archivos
from src.config.settings import config


def _validar_imagen(file_storage):
    if file_storage is None or file_storage.filename == '':
        return None
    datos = file_storage.read()
    if not datos:
        return None
    if file_storage.mimetype not in config.MIME_PERMITIDOS:
        raise ValueError('Formato de imagen no permitido. Usa JPEG, PNG, GIF o WEBP.')
    if len(datos) > config.MAX_CONTENT_LENGTH:
        raise ValueError('La imagen supera el tamaño máximo permitido.')
    return guardar_imagen(datos, file_storage.filename, file_storage.mimetype)


def crear_producto(usuario_id, producto, marca, precio, file_storage=None):
    imagen_info = _validar_imagen(file_storage)
    try:
        idproducto = Producto.crear(usuario_id, producto, marca, precio, imagen_info)
    except Exception:
        if imagen_info and imagen_info['tipo'] != 'blob':
            eliminar_archivos(imagen_info['tipo'], imagen_info.get('ruta'), imagen_info.get('ruta_original'))
        raise

    if imagen_info and imagen_info['tipo'] != 'blob':
        try:
            ImagenMeta.crear(usuario_id, idproducto, imagen_info)
        except Exception:
            eliminar_archivos(imagen_info['tipo'], imagen_info.get('ruta'), imagen_info.get('ruta_original'))
            try:
                Producto.eliminar(usuario_id, idproducto)
            except Exception:
                pass
            raise
    return idproducto


def actualizar_producto(usuario_id, idproducto, producto, marca, precio, file_storage=None, quitar_imagen=False):
    existente = Producto.obtener(usuario_id, idproducto)
    if existente is None:
        raise ValueError('El producto ya no existe o no te pertenece.')

    imagen_info = _validar_imagen(file_storage)
    reemplaza_imagen = imagen_info is not None or quitar_imagen

    Producto.actualizar(usuario_id, idproducto, producto, marca, precio,
                         imagen_info=imagen_info, limpiar_imagen=quitar_imagen)

    if reemplaza_imagen:
        anterior = ImagenMeta.obtener_por_producto(idproducto)
        if anterior:
            eliminar_archivos('comprimida' if anterior.get('ruta_original') else 'cifrada',
                               anterior.get('ruta'), anterior.get('ruta_original'))
            ImagenMeta.eliminar_por_producto(idproducto)
        if imagen_info and imagen_info['tipo'] != 'blob':
            ImagenMeta.crear(usuario_id, idproducto, imagen_info)


def eliminar_producto(usuario_id, idproducto):
    meta = ImagenMeta.obtener_por_producto(idproducto)
    Producto.eliminar(usuario_id, idproducto)
    if meta:
        eliminar_archivos('comprimida' if meta.get('ruta_original') else 'cifrada',
                           meta.get('ruta'), meta.get('ruta_original'))
        ImagenMeta.eliminar_por_producto(idproducto)
