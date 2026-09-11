from src.config.mongo_connection import get_imagenes_collection


class ImagenMeta:
    """Metadatos + ruta en disco de imágenes > 1 MB (tipos 'cifrada' y
    'comprimida'). Las imágenes <= 1 MB no generan documento aquí: viven
    solo como MEDIUMBLOB en MySQL (valor en MongoDB = null, según la
    especificación)."""

    @staticmethod
    def crear(usuario_id, idproducto, imagen_info):
        doc = {
            'usuario_id': usuario_id,
            'idproducto': idproducto,
            'ruta': imagen_info['ruta'],
            'ruta_original': imagen_info.get('ruta_original'),
            'comprimida': imagen_info['comprimida'],
            'mime': imagen_info.get('mime'),
            'nombre': imagen_info.get('nombre'),
            'tamano': imagen_info.get('tamano'),
            'fecha_carga': imagen_info.get('fecha_carga'),
        }
        return get_imagenes_collection().insert_one(doc).inserted_id

    @staticmethod
    def obtener_por_producto(idproducto):
        return get_imagenes_collection().find_one({'idproducto': idproducto})

    @staticmethod
    def eliminar_por_producto(idproducto):
        return get_imagenes_collection().delete_many({'idproducto': idproducto})
