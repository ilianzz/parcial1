# Proyecto 4 (v2) — CRUD con autenticación, MySQL + MongoDB y almacenamiento de imágenes por niveles

Reconstrucción completa del proyecto original sobre la especificación pedida:
autenticación de usuarios, CRUD de productos, y almacenamiento de imágenes
según su peso (BLOB en MySQL / archivo cifrado / archivo cifrado y
comprimido), todo servido a través de endpoints protegidos por JWT.

Se conservan de la versión original: el framework (**Flask**), el nombre de
la tabla `producto` (`producto`, `marca`, `precio`) y los datos de ejemplo
(teclado, monitor, lavadora).

## 1. Arquitectura

```
app.py                        Arranque de Flask, registra blueprints, sirve /static
src/
  config/
    settings.py                Lee TODA la configuración de variables de entorno
    mysql_connection.py
    mongo_connection.py
  models/
    model_usuario.py           CRUD de usuarios (MySQL)
    model_producto.py          CRUD de productos (MySQL), acotado por usuario_id
    model_imagen_meta.py       Metadatos + ruta de imágenes > 1 MB (MongoDB)
  services/
    auth_service.py            Hash de contraseña (Werkzeug) + JWT (PyJWT)
    crypto_service.py          AES-256-GCM (cifrar_bytes / descifrar_bytes)
    image_storage_service.py   Clasifica por peso, comprime, guarda/lee/borra
    producto_service.py        Orquesta producto + imagen a través de MySQL/Mongo/disco
  middleware/
    auth_middleware.py         Decorador @jwt_required
  routes/
    auth_routes.py             POST /api/auth/registro, /api/auth/login
    producto_routes.py         CRUD REST de /api/productos
    imagen_routes.py           Único punto de acceso a las imágenes (protegido)
static/                        Frontend simple (HTML + JS vanilla, sin build step)
dbs/mercancia.sql              Esquema (usuario + producto) y datos de ejemplo
imagenes/                      Archivos cifrados (creado en tiempo de ejecución)
  comprimidas/
seed_demo_user.py              Genera el hash real del usuario demo
pruebas_crud.py                Prueba de integración end-to-end contra las BDs reales
```

## 2. Instalación y ejecución

Requisitos: Python 3.10+, MySQL en ejecución, MongoDB en ejecución.

```bash
python -m venv env
# Windows:  env\Scripts\activate
# Linux/Mac: source env/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env: credenciales de MySQL/Mongo y, sobre todo, genera la clave AES:
python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
# pega el resultado en AES_KEY_BASE64 dentro de .env

mysql -u root -p < dbs/mercancia.sql   # crea el esquema y los datos de ejemplo
python seed_demo_user.py               # fija el password real del usuario demo

python app.py
```

Abrir `http://127.0.0.1:5000/`. Cuenta de prueba: **demo@demo.com / Demo1234!**
(o crea una cuenta nueva desde la pestaña "Crear cuenta").

Verificar con pruebas automatizadas (usa las bases reales, crea y limpia
datos temporales):

```bash
python pruebas_crud.py
```

## 3. Endpoints REST

| Método | Ruta                               | Protegido | Descripción                                   |
|--------|-------------------------------------|:---------:|------------------------------------------------|
| POST   | `/api/auth/registro`               | No        | Crea usuario, devuelve JWT                     |
| POST   | `/api/auth/login`                  | No        | Verifica credenciales, devuelve JWT             |
| GET    | `/api/productos`                   | Sí        | Lista los productos del usuario autenticado     |
| GET    | `/api/productos/<id>`              | Sí        | Detalle de un producto propio                   |
| POST   | `/api/productos`                   | Sí        | Crea producto (multipart, campo `imagen` opcional) |
| PUT    | `/api/productos/<id>`              | Sí        | Edita producto / reemplaza o quita la imagen    |
| DELETE | `/api/productos/<id>`              | Sí        | Elimina producto, metadatos e imagen en disco   |
| GET    | `/api/productos/<id>/imagen`       | Sí        | Vista por defecto (ver punto 5)                 |
| GET    | `/api/productos/<id>/imagen/original` | Sí     | Imagen original, descifrada/descomprimida al vuelo |

Todas las rutas protegidas exigen `Authorization: Bearer <token>`. Un usuario
nunca puede leer, editar, borrar ni ver la imagen de un producto que no le
pertenece (se valida `usuario_id` en cada consulta, no solo en el frontend).

## 4. Lógica de almacenamiento de imágenes (según peso)

| Peso              | Dónde se guarda                 | ¿Cifrada? | ¿Comprimida? | Valor en Mongo |
|-------------------|----------------------------------|:---------:|:-------------:|-----------------|
| ≤ 1 MB            | MySQL, columna `MEDIUMBLOB`      | No        | No            | `null` (no se crea documento) |
| > 1 MB y < 3 MB   | `/imagenes/<uuid>.enc`           | Sí (AES-256-GCM) | No      | Ruta del archivo cifrado |
| ≥ 3 MB            | `/imagenes/comprimidas/<uuid>.enc` (+ `.original.enc`) | Sí | Sí | Ruta de ambos archivos |

La clasificación es automática (`image_storage_service.clasificar_por_peso`),
en base al tamaño real del archivo subido.

### Nota de interpretación (mantenida y ajustada del análisis original)

La especificación pide, para el nivel ≥ 3 MB, mostrar por defecto "la
versión comprimida" y, bajo demanda, "la imagen original descifrada **y
descompimida**". Para que ambas vistas entreguen una imagen realmente
visualizable (no bytes crudos de un compresor genérico tipo gzip), se
generan y cifran **dos archivos** en ese nivel:

- `<uuid>.enc` — recompresión real de la imagen (Pillow, JPEG calidad 60,
  redimensionada si el lado mayor supera 1600 px). Es la vista por defecto.
- `<uuid>.original.enc` — bytes originales sin alterar, solo cifrados. Es
  lo que devuelve `GET /imagenes/original`.

Ambos archivos están cifrados con AES-256-GCM y **nunca se escribe una
copia descifrada en disco**: el descifrado ocurre en memoria dentro del
endpoint protegido y los bytes se devuelven directamente en la respuesta
HTTP. Si la intención original era un único archivo con una compresión
sin pérdida y reversible (p. ej. zlib), avísame y ajusto
`image_storage_service.py` — es el único módulo que habría que tocar.

Para el nivel intermedio (1–3 MB) se mantiene la lectura original del
prompt: se cifra pero no se comprime.

## 5. Seguridad y control de acceso

- **Sin URLs públicas ni estáticas para imágenes.** La carpeta `imagenes/`
  no se registra como `static` en Flask ni se expone por ninguna otra
  ruta; la única forma de obtener bytes de imagen es a través de
  `/api/productos/<id>/imagen[/original]`, que valida el JWT y la
  propiedad del producto antes de leer y descifrar.
- **Cifrado:** AES-256 en modo **GCM** (autenticado: detecta manipulación
  del archivo, no solo confidencialidad). La clave se lee de
  `AES_KEY_BASE64` (variable de entorno), nunca hardcodeada.
- **Contraseñas:** hasheadas con `werkzeug.security.generate_password_hash`
  (PBKDF2 + salt).
- **Sesión:** JWT firmado con `SECRET_KEY` (HS256), expira en 24 h por
  defecto (`JWT_EXP_HORAS`).
- **Subida de imagen:** solo desde archivo local (`input type="file"`).
  No existe ningún campo de URL externa en el formulario ni en el backend.
- **Respuestas de imagen:** `Cache-Control: no-store` para que el
  navegador tampoco conserve una copia persistente fuera de la sesión.

## 6. Frontend

`static/index.html` + `static/js/app.js`, sin dependencias externas ni
build step. Consume la API con `fetch()`, guarda el JWT en
`sessionStorage` (se borra al cerrar la pestaña) y muestra las imágenes
pidiéndolas autenticadas y convirtiéndolas a `Object URL` en memoria
(un `<img src="...">` normal no puede enviar el header `Authorization`).

El botón **"Ver imagen original"** solo aparece en productos de nivel
`comprimida`, pide la imagen bajo demanda y crea otro `Object URL`
temporal — no se guarda ninguna copia en disco del navegador ni del
servidor.

## 7. Diferencias deliberadas frente al proyecto original

- Las imágenes ya no se guardan como **URL externa** en MongoDB: ahora se
  suben desde el dispositivo y se clasifican por peso, como pide la nueva
  especificación. El campo `url` del proyecto anterior desaparece.
- Se agrega autenticación completa; todo el CRUD y las imágenes son
  privados por usuario (antes eran públicos, sin login).
- La "unión" MySQL + Mongo por nombre/heurística del proyecto original ya
  no aplica: ahora la relación es siempre explícita por `idproducto`, y
  Mongo solo existe para los niveles con archivo en disco.
