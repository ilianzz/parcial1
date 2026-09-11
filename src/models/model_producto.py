from src.config.mysql_connection import get_mysql_connection

COLUMNAS = (
    'idproducto, usuario_id, producto, marca, precio, imagen_tipo, '
    'imagen_mime, imagen_nombre, imagen_tamano, creado_en, actualizado_en'
)


class Producto:
    """CRUD de la tabla `producto`. Todas las operaciones están acotadas
    por usuario_id: un usuario nunca puede leer, editar ni borrar
    productos de otro (requisito de control de acceso)."""

    @staticmethod
    def listar(usuario_id):
        connection = get_mysql_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    f'SELECT {COLUMNAS} FROM producto WHERE usuario_id = %s ORDER BY idproducto',
                    (usuario_id,),
                )
                return cursor.fetchall()
        finally:
            connection.close()

    @staticmethod
    def obtener(usuario_id, idproducto):
        connection = get_mysql_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    f'SELECT {COLUMNAS} FROM producto WHERE idproducto = %s AND usuario_id = %s',
                    (idproducto, usuario_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def obtener_con_blob(usuario_id, idproducto):
        """Igual que obtener(), pero incluye imagen_blob. Se separa para
        no traer el BLOB en los listados normales."""
        connection = get_mysql_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    'SELECT * FROM producto WHERE idproducto = %s AND usuario_id = %s',
                    (idproducto, usuario_id),
                )
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def crear(usuario_id, producto, marca, precio, imagen_info=None):
        connection = get_mysql_connection()
        try:
            campos = ['usuario_id', 'producto', 'marca', 'precio']
            valores = [usuario_id, producto, marca, precio]
            if imagen_info:
                campos += ['imagen_tipo', 'imagen_mime', 'imagen_nombre', 'imagen_tamano']
                valores += [imagen_info['tipo'], imagen_info.get('mime'),
                            imagen_info.get('nombre'), imagen_info.get('tamano')]
                if imagen_info['tipo'] == 'blob':
                    campos.append('imagen_blob')
                    valores.append(imagen_info['blob'])
            placeholders = ', '.join(['%s'] * len(valores))
            with connection.cursor() as cursor:
                cursor.execute(
                    f'INSERT INTO producto ({", ".join(campos)}) VALUES ({placeholders})',
                    tuple(valores),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def actualizar(usuario_id, idproducto, producto, marca, precio, imagen_info=None, limpiar_imagen=False):
        connection = get_mysql_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT idproducto FROM producto WHERE idproducto = %s AND usuario_id = %s FOR UPDATE',
                    (idproducto, usuario_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError('El producto ya no existe o no te pertenece.')

                sets = ['producto = %s', 'marca = %s', 'precio = %s']
                valores = [producto, marca, precio]

                if limpiar_imagen and not imagen_info:
                    sets += ['imagen_tipo = NULL', 'imagen_blob = NULL', 'imagen_mime = NULL',
                             'imagen_nombre = NULL', 'imagen_tamano = NULL']
                elif imagen_info:
                    sets += ['imagen_tipo = %s', 'imagen_mime = %s', 'imagen_nombre = %s', 'imagen_tamano = %s']
                    valores += [imagen_info['tipo'], imagen_info.get('mime'),
                                imagen_info.get('nombre'), imagen_info.get('tamano')]
                    if imagen_info['tipo'] == 'blob':
                        sets.append('imagen_blob = %s')
                        valores.append(imagen_info['blob'])
                    else:
                        sets.append('imagen_blob = NULL')

                valores += [idproducto, usuario_id]
                cursor.execute(
                    f'UPDATE producto SET {", ".join(sets)} WHERE idproducto = %s AND usuario_id = %s',
                    tuple(valores),
                )
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def eliminar(usuario_id, idproducto):
        connection = get_mysql_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'DELETE FROM producto WHERE idproducto = %s AND usuario_id = %s',
                    (idproducto, usuario_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError('El producto ya no existe o no te pertenece.')
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
