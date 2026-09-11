"""
Actualiza el password_hash del usuario demo insertado por dbs/mercancia.sql
con un hash real generado por la app (el .sql trae un placeholder porque
el hash depende de la versión de Werkzeug instalada).

Uso:
    python seed_demo_user.py

Credenciales resultantes: demo@demo.com / Demo1234!
"""
from src.config.mysql_connection import get_mysql_connection
from src.services.auth_service import hashear_password

CORREO_DEMO = 'demo@demo.com'
PASSWORD_DEMO = 'Demo1234!'

if __name__ == '__main__':
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE usuario SET password_hash = %s WHERE correo = %s',
                (hashear_password(PASSWORD_DEMO), CORREO_DEMO),
            )
            connection.commit()
            if cursor.rowcount == 1:
                print(f'Usuario demo listo -> correo: {CORREO_DEMO}  password: {PASSWORD_DEMO}')
            else:
                print('No se encontró el usuario demo. ¿Corriste dbs/mercancia.sql primero?')
    finally:
        connection.close()
