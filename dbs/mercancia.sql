-- Esquema MySQL para Proyecto 4 (v2)
-- Conserva la tabla `producto` y los datos de ejemplo del proyecto original,
-- añade `usuario` (autenticación) y las columnas necesarias para el
-- almacenamiento de imágenes por niveles de peso (ver README.md, punto 3).
--
-- ADVERTENCIA: este script elimina el esquema si ya existe (igual que el
-- original). Si tienes datos que conservar, haz un respaldo antes de
-- ejecutarlo, o adapta un script de migración incremental.

DROP SCHEMA IF EXISTS mercancia;
CREATE SCHEMA mercancia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mercancia;

-- ---------------------------------------------------------------
-- Usuarios (autenticación simple)
-- ---------------------------------------------------------------
CREATE TABLE usuario (
  idusuario     INT PRIMARY KEY AUTO_INCREMENT,
  nombre        VARCHAR(200)  NOT NULL,
  correo        VARCHAR(255)  NOT NULL UNIQUE,
  password_hash VARCHAR(255)  NOT NULL,
  creado_en     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------
-- Producto (CRUD principal). Cada producto pertenece a un usuario y
-- puede tener asociada, como máximo, una imagen.
--
-- imagen_tipo indica dónde vive realmente la imagen:
--   NULL        -> el producto no tiene imagen
--   'blob'      -> peso <= 1 MB, bytes en imagen_blob (esta misma tabla)
--   'cifrada'   -> 1 MB < peso < 3 MB, archivo cifrado en /imagenes,
--                  la ruta y metadatos viven en MongoDB
--   'comprimida'-> peso >= 3 MB, archivo comprimido y cifrado en
--                  /imagenes/comprimidas, ruta y metadatos en MongoDB
-- ---------------------------------------------------------------
CREATE TABLE producto (
  idproducto        INT PRIMARY KEY AUTO_INCREMENT,
  usuario_id        INT NOT NULL,
  producto          TEXT NOT NULL,
  marca             TEXT NOT NULL,
  precio            DECIMAL(12,2) NOT NULL,
  imagen_tipo       ENUM('blob', 'cifrada', 'comprimida') NULL,
  imagen_blob       MEDIUMBLOB NULL,          -- solo si imagen_tipo = 'blob'
  imagen_mime       VARCHAR(100) NULL,
  imagen_nombre     VARCHAR(255) NULL,
  imagen_tamano     INT NULL,                 -- peso original en bytes
  creado_en         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                     ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_producto_usuario FOREIGN KEY (usuario_id)
    REFERENCES usuario(idusuario) ON DELETE CASCADE
);

CREATE INDEX idx_producto_usuario ON producto(usuario_id);

-- ---------------------------------------------------------------
-- Datos de ejemplo del proyecto original, asignados a un usuario demo.
-- La contraseña de demo es "Demo1234!" (hash generado con
-- werkzeug.security.generate_password_hash, ver src/services/seed.py).
-- Puedes regenerar el hash real corriendo `python -m src.services.seed`.
-- ---------------------------------------------------------------
INSERT INTO usuario (nombre, correo, password_hash) VALUES
  ('Usuario Demo', 'demo@demo.com', '__REEMPLAZAR_CON_HASH_REAL__');

INSERT INTO producto (usuario_id, producto, marca, precio) VALUES
  (1, 'Teclado mecánico', 'Redragon', 150.00),
  (1, 'Monitor 24 pulgadas', 'Samsung', 900.00),
  (1, 'Lavadora', 'LG', 78945.00);
