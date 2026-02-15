import streamlit as st
import sqlite3
import pandas as pd
import os

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

# Estado de sesión
if 'logged' not in st.session_state:
    st.session_state.logged = False
    st.session_state.is_admin = False
    st.session_state.usuario = None

if 'location_granted' not in st.session_state:
    st.session_state.location_granted = False
    st.session_state.lat = None
    st.session_state.lon = None

# Login
if not st.session_state.logged:
    st.title("Iniciar Sesión")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Entrar"):
            if usuario.strip().lower() == "admin" and contraseña == "1234":
                st.session_state.logged = True
                st.session_state.is_admin = True
                st.session_state.usuario = "admin"
                st.rerun()
            elif contraseña == "demo":
                st.session_state.logged = True
                st.session_state.is_admin = False
                st.session_state.usuario = usuario.strip() or "Usuario"
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

else:
    if st.session_state.is_admin:
        st.title("Panel Administrador")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.rerun()

        conn = get_connection()
        usuarios = ["Todos"] + pd.read_sql_query("SELECT DISTINCT usuario FROM capturas", conn)['usuario'].dropna().unique().tolist()

        filtro_usuario = st.selectbox("Filtrar por usuario", usuarios)

        query = "SELECT * FROM capturas"
        if filtro_usuario != "Todos":
            query += f" WHERE usuario = '{filtro_usuario}'"
        query += " ORDER BY id DESC"

        df = pd.read_sql_query(query, conn)

        def maps_link(row):
            if pd.notna(row.get('latitud')) and pd.notna(row.get('longitud')):
                return f"[Ver en Maps](https://www.google.com/maps?q={row['latitud']},{row['longitud']})"
            return "Sin ubicación"

        if not df.empty:
            df['Ubicación'] = df.apply(maps_link, axis=1)
            st.dataframe(df, use_container_width=True)

        ids = st.multiselect("Eliminar IDs", df['id'].tolist() if not df.empty else [])
        if st.button("Borrar seleccionados") and ids:
            with conn:
                placeholders = ','.join('?' * len(ids))
                conn.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
            st.success(f"Eliminados {len(ids)} registros")
            st.rerun()

    else:
        st.title("Captura de Datos")
        st.markdown(f"Usuario: **{st.session_state.usuario}**")

        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.rerun()

        st.info("Necesitamos tu ubicación actual para registrar el dato.")

        # Solicitud de ubicación con botón visible y detección automática
        if not st.session_state.location_granted:
            st.warning("Pulsa el botón para activar la ubicación")

            if st.button("Obtener mi ubicación", type="primary"):
                st.components.v1.html("""
                    <script>
                    function sendLocation(position) {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        window.parent.postMessage({type: 'location', lat: lat, lon: lon}, "*");
                    }

                    function sendError(error) {
                        window.parent.postMessage({type: 'location_error', msg: error.message}, "*");
                    }

                    navigator.geolocation.getCurrentPosition(sendLocation, sendError, {
                        enableHighAccuracy: true,
                        timeout: 8000,
                        maximumAge: 0
                    });
                    </script>
                """, height=0)

            # Escuchar mensajes del JS (usamos st.components para simular)
            # Nota: Streamlit no tiene listener directo, así que usamos query params como fallback
            if "loc_status" in st.query_params:
                if st.query_params["loc_status"] == "ok":
                    st.session_state.location_granted = True
                    st.session_state.lat = float(st.query_params.get("lat", [0])[0])
                    st.session_state.lon = float(st.query_params.get("lon", [0])[0])
                    st.success("Ubicación obtenida")
                    del st.query_params["loc_status"]
                    del st.query_params["lat"]
                    del st.query_params["lon"]
                    st.rerun()
                else:
                    st.error("Ubicación denegada: " + st.query_params.get("msg", ["error"])[0])
                    del st.query_params["loc_status"]
        else:
            st.success(f"Ubicación: {st.session_state.lat:.5f}, {st.session_state.lon:.5f}")

        # Formulario
        with st.form("form"):
            nombre = st.text_input("Nombre")
            seccion = st.text_input("Sección")
            telefono = st.text_input("Teléfono")
            domicilio = st.text_input("Domicilio")
            edad = st.number_input("Edad", min_value=0, step=1)

            submitted = st.form_submit_button("Guardar", disabled=not st.session_state.location_granted)

            if submitted and st.session_state.location_granted:
                try:
                    with get_connection() as conn:
                        c = conn.cursor()
                        c.execute('''INSERT INTO capturas (usuario, nombre, seccion, telefono, domicilio, edad, latitud, longitud)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (st.session_state.usuario, nombre, seccion, telefono, domicilio, edad,
                                   st.session_state.lat, st.session_state.lon))
                        conn.commit()
                    st.success("Guardado correctamente", icon="✅")
                except Exception as e:
                    st.error(f"Error: {e}")