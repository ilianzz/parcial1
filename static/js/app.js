(() => {
  'use strict';

  const API = '/api';
  let token = sessionStorage.getItem('token') || null;
  let usuarioNombre = sessionStorage.getItem('usuarioNombre') || '';

  // URLs de objeto creadas para imágenes; se revocan al re-renderizar
  // o cerrar modales para no acumular memoria.
  const urlsActivas = new Set();
  function liberarUrls() {
    urlsActivas.forEach(u => URL.revokeObjectURL(u));
    urlsActivas.clear();
  }

  // ---------- Referencias DOM ----------
  const vistaAuth = document.getElementById('vista-auth');
  const vistaInventario = document.getElementById('vista-inventario');
  const sesionInfo = document.getElementById('sesion-info');
  const nombreUsuarioEl = document.getElementById('nombre-usuario');

  const tabs = document.querySelectorAll('.tab');
  const formLogin = document.getElementById('form-login');
  const formRegistro = document.getElementById('form-registro');
  const loginMensaje = document.getElementById('login-mensaje');
  const registroMensaje = document.getElementById('registro-mensaje');

  const listaProductos = document.getElementById('lista-productos');
  const listaVacia = document.getElementById('lista-vacia');
  const inventarioMensaje = document.getElementById('inventario-mensaje');

  const modalProducto = document.getElementById('modal-producto');
  const formProducto = document.getElementById('form-producto');
  const modalTitulo = document.getElementById('modal-titulo');
  const modalMensaje = document.getElementById('modal-mensaje');
  const contenedorQuitarImagen = document.getElementById('contenedor-quitar-imagen');

  const modalEliminar = document.getElementById('modal-eliminar');
  const eliminarTexto = document.getElementById('eliminar-texto');

  const modalOriginal = document.getElementById('modal-original');
  const contenedorOriginal = document.getElementById('contenedor-original');

  let idPendienteEliminar = null;

  // ---------- Helpers de API ----------
  async function apiFetch(ruta, opciones = {}) {
    const headers = opciones.headers || {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const respuesta = await fetch(`${API}${ruta}`, { ...opciones, headers });
    if (respuesta.status === 401) {
      cerrarSesion();
      throw new Error('Tu sesión expiró. Inicia sesión nuevamente.');
    }
    return respuesta;
  }

  function mostrarMensaje(el, texto, tipo) {
    el.textContent = texto;
    el.className = `mensaje ${tipo || ''}`;
  }

  // ---------- Autenticación ----------
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('activo'));
      tab.classList.add('activo');
      const esLogin = tab.dataset.tab === 'login';
      formLogin.classList.toggle('oculto', !esLogin);
      formRegistro.classList.toggle('oculto', esLogin);
    });
  });

  formLogin.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mostrarMensaje(loginMensaje, '', '');
    const datos = Object.fromEntries(new FormData(formLogin));
    try {
      const respuesta = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos),
      });
      const cuerpo = await respuesta.json();
      if (!respuesta.ok) throw new Error(cuerpo.error || 'No se pudo iniciar sesión.');
      iniciarSesion(cuerpo.token, cuerpo.usuario.nombre);
    } catch (error) {
      mostrarMensaje(loginMensaje, error.message, 'error');
    }
  });

  formRegistro.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mostrarMensaje(registroMensaje, '', '');
    const datos = Object.fromEntries(new FormData(formRegistro));
    try {
      const respuesta = await fetch(`${API}/auth/registro`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos),
      });
      const cuerpo = await respuesta.json();
      if (!respuesta.ok) throw new Error(cuerpo.error || 'No se pudo crear la cuenta.');
      iniciarSesion(cuerpo.token, cuerpo.usuario.nombre);
    } catch (error) {
      mostrarMensaje(registroMensaje, error.message, 'error');
    }
  });

  document.getElementById('btn-salir').addEventListener('click', cerrarSesion);

  function iniciarSesion(nuevoToken, nombre) {
    token = nuevoToken;
    usuarioNombre = nombre;
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('usuarioNombre', nombre);
    mostrarInventario();
  }

  function cerrarSesion() {
    token = null;
    usuarioNombre = '';
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('usuarioNombre');
    liberarUrls();
    vistaInventario.classList.add('oculto');
    sesionInfo.classList.add('oculto');
    vistaAuth.classList.remove('oculto');
  }

  function mostrarInventario() {
    vistaAuth.classList.add('oculto');
    vistaInventario.classList.remove('oculto');
    sesionInfo.classList.remove('oculto');
    nombreUsuarioEl.textContent = usuarioNombre;
    cargarProductos();
  }

  // ---------- Listado de productos ----------
  async function cargarProductos() {
    mostrarMensaje(inventarioMensaje, '', '');
    liberarUrls();
    listaProductos.innerHTML = '';
    try {
      const respuesta = await apiFetch('/productos');
      if (!respuesta.ok) throw new Error('No se pudo cargar el inventario.');
      const productos = await respuesta.json();
      listaVacia.classList.toggle('oculto', productos.length > 0);
      for (const producto of productos) {
        listaProductos.appendChild(await crearFicha(producto));
      }
    } catch (error) {
      mostrarMensaje(inventarioMensaje, error.message, 'error');
    }
  }

  async function crearFicha(producto) {
    const ficha = document.createElement('article');
    ficha.className = 'ficha';

    const zonaImagen = document.createElement('div');
    zonaImagen.className = 'ficha-imagen';
    if (producto.tiene_imagen) {
      zonaImagen.innerHTML = '<span class="sin-imagen">Cargando…</span>';
      cargarImagenFicha(producto.idproducto, zonaImagen);
    } else {
      zonaImagen.innerHTML = '<span class="sin-imagen">Sin imagen</span>';
    }

    const cuerpo = document.createElement('div');
    cuerpo.className = 'ficha-cuerpo';
    cuerpo.innerHTML = `
      <div class="ficha-nombre"></div>
      <div class="ficha-marca"></div>
      <div class="ficha-precio"></div>
    `;
    cuerpo.querySelector('.ficha-nombre').textContent = producto.producto;
    cuerpo.querySelector('.ficha-marca').textContent = producto.marca;
    cuerpo.querySelector('.ficha-precio').textContent = `$ ${Number(producto.precio).toFixed(2)}`;

    const acciones = document.createElement('div');
    acciones.className = 'ficha-acciones';
    const btnEditar = document.createElement('button');
    btnEditar.className = 'secundario';
    btnEditar.textContent = 'Editar';
    btnEditar.addEventListener('click', () => abrirModalProducto(producto));
    const btnEliminar = document.createElement('button');
    btnEliminar.className = 'peligro';
    btnEliminar.textContent = 'Eliminar';
    btnEliminar.addEventListener('click', () => abrirModalEliminar(producto));
    acciones.append(btnEditar, btnEliminar);
    cuerpo.appendChild(acciones);

    // Solo las imágenes de nivel "comprimida" (>= 3 MB) tienen una
    // versión distinta que mostrar bajo demanda; para 'blob' y
    // 'cifrada' la vista por defecto YA es la original.
    if (producto.imagen_tipo === 'comprimida') {
      const btnOriginal = document.createElement('button');
      btnOriginal.className = 'btn-ver-original';
      btnOriginal.textContent = 'Ver imagen original';
      btnOriginal.addEventListener('click', () => verImagenOriginal(producto.idproducto));
      cuerpo.appendChild(btnOriginal);
    }

    ficha.append(zonaImagen, cuerpo);
    return ficha;
  }

  async function cargarImagenFicha(idproducto, contenedor) {
    try {
      const respuesta = await apiFetch(`/productos/${idproducto}/imagen`);
      if (!respuesta.ok) throw new Error();
      const blob = await respuesta.blob();
      const url = URL.createObjectURL(blob);
      urlsActivas.add(url);
      contenedor.innerHTML = `<img src="${url}" alt="Imagen del producto">`;
    } catch {
      contenedor.innerHTML = '<span class="sin-imagen">No se pudo cargar</span>';
    }
  }

  async function verImagenOriginal(idproducto) {
    contenedorOriginal.innerHTML = '<span class="sin-imagen">Cargando…</span>';
    modalOriginal.classList.remove('oculto');
    try {
      const respuesta = await apiFetch(`/productos/${idproducto}/imagen/original`);
      if (!respuesta.ok) throw new Error('No se pudo obtener la imagen original.');
      const blob = await respuesta.blob();
      const url = URL.createObjectURL(blob);
      // Esta URL vive solo en memoria del navegador mientras el modal
      // está abierto; no se guarda ninguna copia en disco.
      urlsActivas.add(url);
      contenedorOriginal.innerHTML = `<img src="${url}" alt="Imagen original del producto">`;
    } catch (error) {
      contenedorOriginal.innerHTML = `<span class="sin-imagen">${error.message}</span>`;
    }
  }

  document.getElementById('btn-cerrar-original').addEventListener('click', () => {
    modalOriginal.classList.add('oculto');
    contenedorOriginal.innerHTML = '';
  });

  // ---------- Modal crear/editar ----------
  document.getElementById('btn-nuevo').addEventListener('click', () => abrirModalProducto(null));
  document.getElementById('btn-cancelar').addEventListener('click', cerrarModalProducto);

  function abrirModalProducto(producto) {
    formProducto.reset();
    mostrarMensaje(modalMensaje, '', '');
    if (producto) {
      modalTitulo.textContent = 'Editar producto';
      formProducto.idproducto.value = producto.idproducto;
      formProducto.producto.value = producto.producto;
      formProducto.marca.value = producto.marca;
      formProducto.precio.value = producto.precio;
      contenedorQuitarImagen.classList.toggle('oculto', !producto.tiene_imagen);
    } else {
      modalTitulo.textContent = 'Nuevo producto';
      formProducto.idproducto.value = '';
      contenedorQuitarImagen.classList.add('oculto');
    }
    modalProducto.classList.remove('oculto');
  }

  function cerrarModalProducto() {
    modalProducto.classList.add('oculto');
  }

  formProducto.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    mostrarMensaje(modalMensaje, 'Guardando…', '');
    const idproducto = formProducto.idproducto.value;
    const cuerpo = new FormData(formProducto);
    if (!cuerpo.get('quitar_imagen')) cuerpo.delete('quitar_imagen');
    else cuerpo.set('quitar_imagen', '1');

    try {
      const respuesta = await apiFetch(
        idproducto ? `/productos/${idproducto}` : '/productos',
        { method: idproducto ? 'PUT' : 'POST', body: cuerpo },
      );
      const datos = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) throw new Error(datos.error || 'No se pudo guardar el producto.');
      cerrarModalProducto();
      await cargarProductos();
    } catch (error) {
      mostrarMensaje(modalMensaje, error.message, 'error');
    }
  });

  // ---------- Modal eliminar ----------
  function abrirModalEliminar(producto) {
    idPendienteEliminar = producto.idproducto;
    eliminarTexto.textContent = `¿Eliminar "${producto.producto}"? Esta acción no se puede deshacer.`;
    modalEliminar.classList.remove('oculto');
  }

  document.getElementById('btn-cancelar-eliminar').addEventListener('click', () => {
    modalEliminar.classList.add('oculto');
    idPendienteEliminar = null;
  });

  document.getElementById('btn-confirmar-eliminar').addEventListener('click', async () => {
    if (idPendienteEliminar == null) return;
    try {
      const respuesta = await apiFetch(`/productos/${idPendienteEliminar}`, { method: 'DELETE' });
      if (!respuesta.ok && respuesta.status !== 204) {
        const datos = await respuesta.json().catch(() => ({}));
        throw new Error(datos.error || 'No se pudo eliminar el producto.');
      }
      modalEliminar.classList.add('oculto');
      idPendienteEliminar = null;
      await cargarProductos();
    } catch (error) {
      mostrarMensaje(inventarioMensaje, error.message, 'error');
    }
  });

  // ---------- Arranque ----------
  if (token) {
    mostrarInventario();
  }
})();
