from flask import Flask, send_from_directory
from src.config.settings import config
from src.routes.auth_routes import auth_bp
from src.routes.producto_routes import producto_bp
from src.routes.imagen_routes import imagen_bp

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

app.register_blueprint(auth_bp)
app.register_blueprint(producto_bp)
app.register_blueprint(imagen_bp)


@app.route('/')
def index():
    # Frontend simple servido como estático; consume la API vía fetch().
    return send_from_directory(app.static_folder, 'index.html')


@app.errorhandler(413)
def demasiado_grande(_error):
    return {'error': 'El archivo supera el tamaño máximo permitido.'}, 413


if __name__ == '__main__':
    app.run(debug=True)
