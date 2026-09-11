from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, g
from src.middleware.auth_middleware import jwt_required
from src.models.model_producto import Producto
from src.services.producto_service import crear_producto, actualizar_producto, eliminar_producto

producto_bp = Blueprint('producto_bp', __name__, url_prefix='/api/productos')


def _serializar(fila):
    return {
        'idproducto': fila['idproducto'],
        'producto': fila['producto'],
        'marca': fila['marca'],
        'precio': str(fila['precio']),
        'tiene_imagen': fila['imagen_tipo'] is not None,
        'imagen_tipo': fila['imagen_tipo'],
        'imagen_nombre': fila.get('imagen_nombre'),
        'creado_en': fila['creado_en'].isoformat() if fila.get('creado_en') else None,
        'actualizado_en': fila['actualizado_en'].isoformat() if fila.get('actualizado_en') else None,
    }


def _validar_campos(form):
    producto = (form.get('producto') or '').strip()
    marca = (form.get('marca') or '').strip()
    precio_raw = (form.get('precio') or '').strip()

    if not producto or not marca:
        raise ValueError('Producto y marca son obligatorios.')
    if len(producto) > 200 or len(marca) > 200:
        raise ValueError('Producto y marca no pueden superar 200 caracteres.')
    try:
        precio = Decimal(precio_raw)
        if not precio.is_finite() or precio < 0 or precio > Decimal('9999999999.99') \
                or precio != precio.quantize(Decimal('0.01')):
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValueError('El precio debe ser un número positivo, con máximo dos decimales.')
    return producto, marca, precio


@producto_bp.route('', methods=['GET'])
@jwt_required
def listar():
    filas = Producto.listar(g.usuario_id)
    return jsonify([_serializar(f) for f in filas]), 200


@producto_bp.route('/<int:idproducto>', methods=['GET'])
@jwt_required
def obtener(idproducto):
    fila = Producto.obtener(g.usuario_id, idproducto)
    if fila is None:
        return jsonify({'error': 'Producto no encontrado.'}), 404
    return jsonify(_serializar(fila)), 200


@producto_bp.route('', methods=['POST'])
@jwt_required
def crear():
    try:
        producto, marca, precio = _validar_campos(request.form)
        archivo = request.files.get('imagen')
        idproducto = crear_producto(g.usuario_id, producto, marca, precio, archivo)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    fila = Producto.obtener(g.usuario_id, idproducto)
    return jsonify(_serializar(fila)), 201


@producto_bp.route('/<int:idproducto>', methods=['PUT'])
@jwt_required
def actualizar(idproducto):
    try:
        producto, marca, precio = _validar_campos(request.form)
        archivo = request.files.get('imagen')
        quitar_imagen = request.form.get('quitar_imagen') == '1'
        actualizar_producto(g.usuario_id, idproducto, producto, marca, precio, archivo, quitar_imagen)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    fila = Producto.obtener(g.usuario_id, idproducto)
    return jsonify(_serializar(fila)), 200


@producto_bp.route('/<int:idproducto>', methods=['DELETE'])
@jwt_required
def eliminar(idproducto):
    try:
        eliminar_producto(g.usuario_id, idproducto)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return '', 204
