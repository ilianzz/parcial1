"""
Único punto de acceso a las imágenes. No existe ninguna ruta estática
que sirva /imagenes/* directamente (Flask no la registra en ningún
lado): todo pasa por aquí, con JWT validado y verificación de que el
producto pertenece al usuario autenticado.
"""
from flask import Blueprint, g, jsonify, Response
from src.middleware.auth_middleware import jwt_required
from src.models.model_producto import Producto
from src.models.model_imagen_meta import ImagenMeta
from src.services.image_storage_service import leer_imagen_default, leer_imagen_original

imagen_bp = Blueprint('imagen_bp', __name__, url_prefix='/api/productos')


def _sin_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    return response


@imagen_bp.route('/<int:idproducto>/imagen', methods=['GET'])
@jwt_required
def imagen_default(idproducto):
    fila = Producto.obtener_con_blob(g.usuario_id, idproducto)
    if fila is None or fila['imagen_tipo'] is None:
        return jsonify({'error': 'Este producto no tiene imagen.'}), 404

    if fila['imagen_tipo'] == 'blob':
        datos = fila['imagen_blob']
    else:
        meta = ImagenMeta.obtener_por_producto(idproducto)
        if meta is None:
            return jsonify({'error': 'No se encontraron los metadatos de la imagen.'}), 404
        datos = leer_imagen_default(fila['imagen_tipo'], meta['ruta'])

    mime = fila['imagen_mime'] or 'application/octet-stream'
    if fila['imagen_tipo'] == 'comprimida':
        mime = 'image/jpeg'  # la versión por defecto siempre se recomprime a JPEG
    return _sin_cache(Response(datos, mimetype=mime))


@imagen_bp.route('/<int:idproducto>/imagen/original', methods=['GET'])
@jwt_required
def imagen_original(idproducto):
    fila = Producto.obtener_con_blob(g.usuario_id, idproducto)
    if fila is None or fila['imagen_tipo'] is None:
        return jsonify({'error': 'Este producto no tiene imagen.'}), 404

    if fila['imagen_tipo'] == 'blob':
        datos = fila['imagen_blob']
        mime = fila['imagen_mime'] or 'application/octet-stream'
    else:
        meta = ImagenMeta.obtener_por_producto(idproducto)
        if meta is None:
            return jsonify({'error': 'No se encontraron los metadatos de la imagen.'}), 404
        datos = leer_imagen_original(fila['imagen_tipo'], meta['ruta'], meta.get('ruta_original'))
        mime = meta.get('mime') or 'application/octet-stream'

    return _sin_cache(Response(datos, mimetype=mime))
