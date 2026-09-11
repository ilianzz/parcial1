"""
Prueba de integración end-to-end. Crea un usuario y productos temporales
usando el cliente de pruebas de Flask contra las bases MySQL/MongoDB
reales configuradas en .env, y los limpia al terminar (éxito o error).

Cubre:
  - registro, login, y que las rutas de productos/imagen exigen JWT.
  - creación de producto sin imagen.
  - los tres niveles de imagen (blob / cifrada / comprimida) según peso,
    incluyendo que el archivo en disco queda cifrado (no es la imagen
    en claro) y que los endpoints de descarga la devuelven correcta.
  - "ver imagen original" en el nivel comprimida.
  - actualización (reemplazo de imagen) y eliminación (borra fila,
    documento Mongo y archivos en disco).
  - que un usuario no puede ver ni modificar productos de otro.

Ejecutar:  python pruebas_crud.py   (requiere MySQL y MongoDB disponibles
y las variables de entorno de .env, incluida AES_KEY_BASE64).
"""
import io
import os
from uuid import uuid4

from PIL import Image

from app import app
from src.config.mysql_connection import get_mysql_connection
from src.config.mongo_connection import get_imagenes_collection
from src.services.crypto_service import descifrar_bytes


def _imagen_jpeg(ancho, alto, calidad=95):
    """Genera una imagen JPEG de ruido aleatorio; el ruido comprime mal,
    lo que permite superar 1 MB o 3 MB con dimensiones razonables."""
    datos_aleatorios = os.urandom(ancho * alto * 3)
    imagen = Image.frombytes('RGB', (ancho, alto), datos_aleatorios)
    salida = io.BytesIO()
    imagen.save(salida, format='JPEG', quality=calidad)
    return salida.getvalue()


def _limpiar(sufijo, ids_producto):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM usuario WHERE correo LIKE %s', (f'%{sufijo}%',))
        connection.commit()
    finally:
        connection.close()
    if ids_producto:
        get_imagenes_collection().delete_many({'idproducto': {'$in': ids_producto}})


def probar():
    sufijo = uuid4().hex[:12]
    correo_a = f'prueba_{sufijo}_a@test.local'
    correo_b = f'prueba_{sufijo}_b@test.local'
    client = app.test_client()
    ids_producto = []

    try:
        # ---------- Rutas protegidas exigen token ----------
        assert client.get('/api/productos').status_code == 401

        # ---------- Registro y login ----------
        r = client.post('/api/auth/registro', json={
            'nombre': 'Prueba A', 'correo': correo_a, 'password': 'ClaveSegura1',
        })
        assert r.status_code == 201, r.get_json()
        token_a = r.get_json()['token']
        header_a = {'Authorization': f'Bearer {token_a}'}

        r = client.post('/api/auth/registro', json={
            'nombre': 'Prueba B', 'correo': correo_b, 'password': 'ClaveSegura1',
        })
        token_b = r.get_json()['token']
        header_b = {'Authorization': f'Bearer {token_b}'}

        r = client.post('/api/auth/login', json={'correo': correo_a, 'password': 'incorrecta'})
        assert r.status_code == 401

        # ---------- Crear producto sin imagen ----------
        r = client.post('/api/productos', data={
            'producto': '__prueba_sin_imagen', 'marca': 'X', 'precio': '10.00',
        }, headers=header_a)
        assert r.status_code == 201, r.get_json()
        idp_sin_imagen = r.get_json()['idproducto']
        ids_producto.append(idp_sin_imagen)
        assert r.get_json()['tiene_imagen'] is False

        # ---------- Nivel BLOB (<= 1 MB) ----------
        imagen_chica = _imagen_jpeg(40, 40)
        assert len(imagen_chica) <= 1 * 1024 * 1024
        r = client.post('/api/productos', data={
            'producto': '__prueba_blob', 'marca': 'X', 'precio': '10.00',
            'imagen': (io.BytesIO(imagen_chica), 'chica.jpg', 'image/jpeg'),
        }, content_type='multipart/form-data', headers=header_a)
        assert r.status_code == 201, r.get_json()
        idp_blob = r.get_json()['idproducto']
        ids_producto.append(idp_blob)
        assert r.get_json()['imagen_tipo'] == 'blob'
        assert get_imagenes_collection().find_one({'idproducto': idp_blob}) is None  # null en Mongo

        r = client.get(f'/api/productos/{idp_blob}/imagen', headers=header_a)
        assert r.status_code == 200 and r.data == imagen_chica

        # ---------- Nivel CIFRADA (1 MB < peso < 3 MB) ----------
        imagen_mediana = _imagen_jpeg(900, 700, calidad=100)
        assert 1 * 1024 * 1024 < len(imagen_mediana) < 3 * 1024 * 1024, len(imagen_mediana)
        r = client.post('/api/productos', data={
            'producto': '__prueba_cifrada', 'marca': 'X', 'precio': '10.00',
            'imagen': (io.BytesIO(imagen_mediana), 'mediana.jpg', 'image/jpeg'),
        }, content_type='multipart/form-data', headers=header_a)
        assert r.status_code == 201, r.get_json()
        idp_cifrada = r.get_json()['idproducto']
        ids_producto.append(idp_cifrada)
        assert r.get_json()['imagen_tipo'] == 'cifrada'
        meta = get_imagenes_collection().find_one({'idproducto': idp_cifrada})
        assert meta is not None and meta['comprimida'] is False
        # El archivo en disco NO debe ser la imagen en claro.
        with open(meta['ruta'], 'rb') as f:
            crudo = f.read()
        assert crudo != imagen_mediana
        assert descifrar_bytes(crudo) == imagen_mediana

        r = client.get(f'/api/productos/{idp_cifrada}/imagen', headers=header_a)
        assert r.status_code == 200 and r.data == imagen_mediana

        # ---------- Nivel COMPRIMIDA (peso >= 3 MB) ----------
        imagen_grande = _imagen_jpeg(1700, 1300, calidad=100)
        assert len(imagen_grande) >= 3 * 1024 * 1024, len(imagen_grande)
        r = client.post('/api/productos', data={
            'producto': '__prueba_comprimida', 'marca': 'X', 'precio': '10.00',
            'imagen': (io.BytesIO(imagen_grande), 'grande.jpg', 'image/jpeg'),
        }, content_type='multipart/form-data', headers=header_a)
        assert r.status_code == 201, r.get_json()
        idp_comprimida = r.get_json()['idproducto']
        ids_producto.append(idp_comprimida)
        assert r.get_json()['imagen_tipo'] == 'comprimida'
        meta = get_imagenes_collection().find_one({'idproducto': idp_comprimida})
        assert meta is not None and meta['comprimida'] is True and meta['ruta_original']

        r = client.get(f'/api/productos/{idp_comprimida}/imagen', headers=header_a)
        assert r.status_code == 200
        vista_default = r.data
        assert len(vista_default) < len(imagen_grande)  # la vista por defecto es más liviana

        r = client.get(f'/api/productos/{idp_comprimida}/imagen/original', headers=header_a)
        assert r.status_code == 200 and r.data == imagen_grande  # el original se recupera exacto

        # ---------- Control de acceso entre usuarios ----------
        assert client.get(f'/api/productos/{idp_blob}', headers=header_b).status_code == 404
        assert client.get(f'/api/productos/{idp_blob}/imagen', headers=header_b).status_code == 404
        assert client.delete(f'/api/productos/{idp_blob}', headers=header_b).status_code == 400

        # ---------- Actualizar reemplazando la imagen (comprimida -> blob) ----------
        r = client.put(f'/api/productos/{idp_comprimida}', data={
            'producto': '__prueba_comprimida', 'marca': 'X', 'precio': '15.00',
            'imagen': (io.BytesIO(imagen_chica), 'chica.jpg', 'image/jpeg'),
        }, content_type='multipart/form-data', headers=header_a)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['imagen_tipo'] == 'blob'
        assert get_imagenes_collection().find_one({'idproducto': idp_comprimida}) is None
        assert not os.path.exists(meta['ruta'])
        assert not os.path.exists(meta['ruta_original'])

        # ---------- Eliminar ----------
        r = client.delete(f'/api/productos/{idp_cifrada}', headers=header_a)
        assert r.status_code == 204
        assert client.get(f'/api/productos/{idp_cifrada}', headers=header_a).status_code == 404
        assert get_imagenes_collection().find_one({'idproducto': idp_cifrada}) is None

        print('OK: registro/login, JWT obligatorio, niveles blob/cifrada/comprimida, '
              'cifrado en disco verificado, imagen original bajo demanda, control de '
              'acceso entre usuarios, actualización con reemplazo y eliminación.')
    finally:
        _limpiar(sufijo, ids_producto)


if __name__ == '__main__':
    probar()
