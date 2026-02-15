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
    st.session_state.location_error = None

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
                df['Mapa'] = df.apply(
                    lambda row: f"[Ver mapa](https://www.google.com/maps?q={row['latitud']},{row['longitud']})"
                    if pd.notnull(row['latitud']) and pd.notnull(row['longitud']) else "Sin ubicación",
                    axis=1
                )

            if df.empty:
                st.info("No hay registros.")
            else:
                st.dataframe(df, use_container_width=True)

            st.subheader("Eliminar")
            ids = st.multiselect("IDs a borrar", df['id'].tolist())
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
        st.subheader("Necesitamos tu ubicación actual")
        
        if not st.session_state.location_granted and not st.session_state.location_error:
            st.info("Pulsa el botón para permitir el acceso a tu ubicación.")
            
            if st.button("Permitir ubicación"):
                js_code = """
                <script>
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        window.parent.postMessage({
                            type: 'location_success',
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        }, "*");
                    },
                    (error) => {
                        window.parent.postMessage({
                            type: 'location_error',
                            code: error.code,
                            message: error.message
                        }, "*");
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                );
                </script>
                """

                st.components.v1.html(js_code, height=0)

                # Mostrar mensaje mientras espera
                st.info("Esperando respuesta del navegador... (puede tardar unos segundos)")

        # Escuchar respuesta del JS (se ejecuta en cada rerun)
        if st.session_state.location_granted:
            st.success(f"Ubicación obtenida: Lat {st.session_state.lat:.6f}, Lng {st.session_state.lng:.6f}")
            # Aquí va el formulario
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
                        st.error("Teléfono inválido (10 dígitos)")
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
                        except Exception as e:
                            st.error(f"Error: {e}")

        elif st.session_state.location_error:
            st.error(f"No se pudo obtener la ubicación: {st.session_state.location_error}")
            st.warning("Debes permitir el acceso a la ubicación para continuar.")
            st.stop()  # Bloquea todo

        # Escuchar mensajes de JS (se hace en cada rerun)
        if "location_success" in st.experimental_get_query_params():
            try:
                params = st.experimental_get_query_params()
                st.session_state.lat = float(params["lat"][0])
                st.session_state.lng = float(params["lng"][0])
                st.session_state.location_granted = True
                st.session_state.location_error = None
                st.experimental_set_query_params()  # Limpiar params
                st.rerun()
            except:
                pass

        if "location_error" in st.experimental_get_query_params():
            try:
                params = st.experimental_get_query_params()
                code = params["code"][0]
                msg = params["message"][0]
                st.session_state.location_error = f"Error {code}: {msg}"
                st.session_state.location_granted = False
                st.experimental_set_query_params()
                st.rerun()
            except:
                pass