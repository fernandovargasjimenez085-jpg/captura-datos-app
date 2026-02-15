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

if 'lat' not in st.session_state:
    st.session_state.lat = None
    st.session_state.lng = None
    st.session_state.location_granted = False

# ─── LOGIN ────────────────────────────────────────────────────────────────
if not st.session_state.logged:
    st.title("Iniciar Sesión")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Entrar", type="primary"):
            if not usuario or not contraseña:
                st.error("Ingresa usuario y contraseña")
            else:
                if usuario.strip().lower() == "admin" and contraseña == "1234":
                    st.session_state.logged = True
                    st.session_state.is_admin = True
                    st.session_state.usuario = "admin"
                    st.rerun()
                elif contraseña == "demo":
                    st.session_state.logged = True
                    st.session_state.is_admin = False
                    st.session_state.usuario = usuario.strip()
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")

else:
    if st.session_state.is_admin:
        # ─── PANEL ADMIN ──────────────────────────────────────────────────────
        st.title("Panel Administrador")
        st.markdown(f"Logueado como: **{st.session_state.usuario}**")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.usuario = None
            st.rerun()

        try:
            conn = get_connection()
            usuarios_df = pd.read_sql_query("SELECT DISTINCT usuario FROM capturas WHERE usuario IS NOT NULL ORDER BY usuario", conn)
            usuarios = ["Todos"] + usuarios_df['usuario'].tolist()

            usuario_sel = st.selectbox("Filtrar por usuario", usuarios)

            query = "SELECT id, usuario, nombre, seccion, telefono, domicilio, edad, latitud, longitud FROM capturas"
            params = ()
            if usuario_sel != "Todos":
                query += " WHERE usuario = ?"
                params = (usuario_sel,)

            query += " ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                # Crear link a Google Maps
                df['Mapa'] = df.apply(
                    lambda row: f"[Ver en Google Maps](https://www.google.com/maps?q={row['latitud']},{row['longitud']})" 
                    if pd.notnull(row['latitud']) and pd.notnull(row['longitud']) else "Sin ubicación",
                    axis=1
                )

            if df.empty:
                st.info("No hay registros para el filtro seleccionado.")
            else:
                st.dataframe(df, use_container_width=True)

            # Eliminar
            st.subheader("Eliminar registros")
            ids = st.multiselect("Selecciona IDs", df['id'].tolist())
            if st.button("Borrar seleccionados") and ids:
                with conn:
                    c = conn.cursor()
                    placeholders = ','.join('?' * len(ids))
                    c.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
                st.success(f"Eliminados {len(ids)} registros")
                st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")

    else:
        # ─── USUARIO NORMAL ───────────────────────────────────────────────────
        st.title("Captura de Datos")
        st.markdown(f"Logueado como: **{st.session_state.usuario}**")

        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.usuario = None
            st.rerun()

        # ─── SOLICITUD DE UBICACIÓN ───────────────────────────────────────────
        if not st.session_state.location_granted:
            st.warning("Esta aplicación necesita tu ubicación para continuar.")
            st.info("Por favor permite el acceso a la ubicación cuando el navegador te lo pregunte.")

            # JavaScript para pedir ubicación
            js_code = """
            <script>
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    window.parent.postMessage({
                        type: 'streamlit:geolocation',
                        lat: lat,
                        lng: lng
                    }, "*");
                },
                (error) => {
                    window.parent.postMessage({
                        type: 'streamlit:geolocation_error',
                        code: error.code,
                        message: error.message
                    }, "*");
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
            </script>
            """

            st.components.v1.html(js_code, height=0)

            # Escuchar respuesta de JS
            if "geolocation" in st.query_params:
                try:
                    lat = float(st.query_params["lat"][0])
                    lng = float(st.query_params["lng"][0])
                    st.session_state.lat = lat
                    st.session_state.lng = lng
                    st.session_state.location_granted = True
                    st.success("Ubicación obtenida correctamente.")
                    st.rerun()
                except:
                    pass

            if "geolocation_error" in st.query_params:
                code = st.query_params["code"][0]
                msg = st.query_params["message"][0]
                st.error(f"No se pudo obtener la ubicación: {msg} (código {code})")
                st.warning("Debes permitir el acceso a la ubicación para continuar.")
                st.stop()  # BLOQUEA el avance

        else:
            # Formulario solo aparece si ya tenemos ubicación
            st.success(f"Ubicación actual: Lat {st.session_state.lat:.6f}, Lng {st.session_state.lng:.6f}")

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
                        st.error("El teléfono debe tener 10 dígitos numéricos")
                    else:
                        try:
                            with get_connection() as conn:
                                c = conn.cursor()
                                c.execute('''INSERT INTO capturas 
                                             (usuario, nombre, seccion, telefono, domicilio, edad, latitud, longitud)
                                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                          (st.session_state.usuario, nombre, seccion, telefono, domicilio, edad,
                                           st.session_state.lat, st.session_state.lng))
                                conn.commit()
                            st.success("¡Registro guardado correctamente!", icon="✅")
                            st.toast("Datos registrados con éxito", icon="✅")
                            # Limpiar ubicación después de guardar (opcional)
                            # st.session_state.location_granted = False
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")