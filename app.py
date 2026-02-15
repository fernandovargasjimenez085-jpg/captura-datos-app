import streamlit as st
import sqlite3
import pandas as pd
import os

# ────────────────────────────────────────────────
# Configuración general
# ────────────────────────────────────────────────
st.set_page_config(page_title="Captura de Datos - DEMO", layout="wide")

DB_PATH = "datos.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS capturas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT,
                        nombre TEXT,
                        seccion TEXT,
                        telefono TEXT,
                        domicilio TEXT,
                        edad INTEGER,
                        latitud REAL,
                        longitud REAL
                     )''')
        conn.commit()

init_db()

# ────────────────────────────────────────────────
# Estado de sesión
# ────────────────────────────────────────────────
if 'logged' not in st.session_state:
    st.session_state.logged = False
    st.session_state.is_admin = False
    st.session_state.usuario = None

if 'location_granted' not in st.session_state:
    st.session_state.location_granted = False
    st.session_state.lat = None
    st.session_state.lon = None

# ────────────────────────────────────────────────
# Pantalla de login
# ────────────────────────────────────────────────
if not st.session_state.logged:
    st.title("Iniciar Sesión")
    st.markdown("Ingresa tus credenciales para continuar")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("Usuario", placeholder="Ej: admin o tu nombre")
        contraseña = st.text_input("Contraseña", type="password", placeholder="Ej: 1234 o demo")

        if st.button("Entrar", type="primary", use_container_width=True):
            if not usuario or not contraseña:
                st.error("Ingresa usuario y contraseña")
            else:
                if usuario.strip().lower() == "admin" and contraseña == "1234":
                    st.session_state.logged = True
                    st.session_state.is_admin = True
                    st.session_state.usuario = "admin"
                    st.success("Bienvenido Administrador")
                    st.rerun()
                elif contraseña == "demo":
                    st.session_state.logged = True
                    st.session_state.is_admin = False
                    st.session_state.usuario = usuario.strip()
                    st.success(f"Bienvenido {usuario.strip()}")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

else:
    # ────────────────────────────────────────────────
    # Vista según rol
    # ────────────────────────────────────────────────
    if st.session_state.is_admin:
        st.title("🛠 Panel Administrador")
        st.markdown(f"Logueado como: **{st.session_state.usuario}**")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.is_admin = False
            st.session_state.usuario = None
            st.rerun()

        try:
            conn = get_connection()
            usuarios_df = pd.read_sql_query("SELECT DISTINCT usuario FROM capturas WHERE usuario IS NOT NULL ORDER BY usuario", conn)
            usuarios = ["Todos"] + usuarios_df['usuario'].tolist()

            usuario_seleccionado = st.selectbox("Filtrar por usuario que registró", usuarios)

            query = "SELECT id, usuario, nombre, seccion, telefono, domicilio, edad, latitud, longitud FROM capturas"
            params = ()
            if usuario_seleccionado != "Todos":
                query += " WHERE usuario = ?"
                params = (usuario_seleccionado,)

            query += " ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                st.info("No hay registros para el filtro seleccionado.")
            else:
                def maps_link(row):
                    if pd.notna(row['latitud']) and pd.notna(row['longitud']):
                        url = f"https://www.google.com/maps?q={row['latitud']},{row['longitud']}"
                        return f'<a href="{url}" target="_blank">Ver en Google Maps</a>'
                    return "Sin ubicación"

                df['Ubicación'] = df.apply(maps_link, axis=1)
                st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

            st.subheader("Eliminar registros")
            ids = st.multiselect("Selecciona los ID a borrar", options=df['id'].tolist())
            if st.button("Borrar seleccionados") and ids:
                with conn:
                    c = conn.cursor()
                    placeholders = ','.join('?' for _ in ids)
                    c.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
                st.success(f"Se eliminaron {len(ids)} registro(s)")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer la base de datos: {e}")

    else:
        # ────────────────────────────────────────────────
        # Vista de usuario normal con solicitud visible de ubicación
        # ────────────────────────────────────────────────
        st.title("📝 Captura de Datos")
        st.markdown(f"Logueado como: **{st.session_state.usuario}**")

        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.usuario = None
            st.session_state.location_granted = False
            st.session_state.lat = None
            st.session_state.lon = None
            st.rerun()

        # Solicitud visible de ubicación
        st.info("**Importante:** Para continuar, necesitamos tu ubicación actual. Esto permite asociar el registro con tu posición geográfica.")

        if not st.session_state.location_granted:
            st.warning("Haz clic en el botón para permitir el acceso a tu ubicación")

            if st.button("Activar mi ubicación", type="primary", key="request_location"):
                st.components.v1.html("""
                    <script>
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            const url = new URL(window.location);
                            url.searchParams.set('location_status', 'success');
                            url.searchParams.set('lat', lat);
                            url.searchParams.set('lon', lon);
                            window.location = url;
                        },
                        (error) => {
                            const url = new URL(window.location);
                            url.searchParams.set('location_status', 'error');
                            window.location = url;
                        },
                        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                    );
                    </script>
                """, height=0)

            # Leer parámetros de la URL después de la recarga
            if "location_status" in st.query_params:
                status = st.query_params["location_status"]
                if status == "success" and "lat" in st.query_params and "lon" in st.query_params:
                    st.session_state.location_granted = True
                    st.session_state.lat = float(st.query_params["lat"])
                    st.session_state.lon = float(st.query_params["lon"])
                    st.success("¡Ubicación obtenida correctamente!")
                    # Limpiar parámetros para evitar loops
                    del st.query_params["location_status"]
                    del st.query_params["lat"]
                    del st.query_params["lon"]
                    st.rerun()
                elif status == "error":
                    st.session_state.location_granted = False
                    st.error("No se pudo obtener la ubicación. Debes permitir el acceso para poder guardar registros.")
                    st.info("Por favor activa la ubicación y vuelve a intentarlo.")
                    # Limpiar parámetros
                    del st.query_params["location_status"]
        else:
            st.success(f"Ubicación activa: {st.session_state.lat:.6f}, {st.session_state.lon:.6f}")

        # Formulario (solo visible si hay ubicación)
        if st.session_state.location_granted:
            with st.form("form_captura", clear_on_submit=True):
                nombre    = st.text_input("1. Nombre")
                seccion   = st.text_input("2. Sección")
                telefono  = st.text_input("3. Teléfono", max_chars=10)
                domicilio = st.text_input("4. Domicilio")
                edad      = st.number_input("5. Edad", min_value=0, max_value=120, step=1)

                if st.form_submit_button("Guardar"):
                    if not all([nombre, seccion, telefono, domicilio, edad]):
                        st.error("Todos los campos son obligatorios")
                    elif len(telefono) != 10 or not telefono.isdigit():
                        st.error("El teléfono debe tener exactamente 10 dígitos numéricos")
                    else:
                        try:
                            with get_connection() as conn:
                                c = conn.cursor()
                                c.execute('''INSERT INTO capturas 
                                             (usuario, nombre, seccion, telefono, domicilio, edad, latitud, longitud)
                                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                          (st.session_state.usuario, nombre, seccion, telefono, domicilio, edad,
                                           st.session_state.lat, st.session_state.lon))
                                conn.commit()
                            st.success("¡Registro guardado correctamente!", icon="✅")
                            st.toast("Datos registrados con éxito", icon="✅")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
        else:
            st.warning("No puedes guardar registros hasta que actives tu ubicación.")