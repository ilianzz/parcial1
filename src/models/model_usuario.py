from src.config.mysql_connection import get_mysql_connection


class Usuario:

    @staticmethod
    def crear(nombre, correo, password_hash):
        connection = get_mysql_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'INSERT INTO usuario (nombre, correo, password_hash) VALUES (%s, %s, %s)',
                    (nombre, correo, password_hash),
                )
                connection.commit()
                return cursor.lastrowid
        finally:
            connection.close()

    @staticmethod
    def buscar_por_correo(correo):
        connection = get_mysql_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT * FROM usuario WHERE correo = %s', (correo,))
                return cursor.fetchone()
        finally:
            connection.close()

    @staticmethod
    def buscar_por_id(usuario_id):
        connection = get_mysql_connection()
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT idusuario, nombre, correo, creado_en FROM usuario WHERE idusuario = %s', (usuario_id,))
                return cursor.fetchone()
        finally:
            connection.close()
