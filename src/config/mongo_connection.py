from pymongo import MongoClient
from src.config.settings import config

_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)


def get_mongo_db():
    return _client[config.MONGO_DATABASE]


def get_imagenes_collection():
    """Colección con metadatos + ruta en disco de imágenes > 1 MB.

    Documento:
      idproducto   -> vincula con MySQL (producto.idproducto)
      usuario_id   -> dueño (control de acceso adicional)
      ruta         -> ruta del archivo cifrado en disco
      ruta_original-> (solo tipo 'comprimida') ruta del archivo original
                       cifrado, sin comprimir, para "ver imagen original"
      comprimida   -> bool
      mime         -> tipo mime original de la imagen
      nombre       -> nombre de archivo original
      tamano       -> peso original en bytes
      fecha_carga  -> datetime
    """
    return get_mongo_db().imagenes
