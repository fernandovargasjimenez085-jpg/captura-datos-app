import streamlit as st
import sqlite3
import pandas as pd
import os

# ────────────────────────────────────────────────
# Configuración
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
                        edad INTEGER
                     )''')
        conn.commit()

init_db()

# ────────────────────────────────────────────────
# Estado de sesión para login
# ────────────────────────────────────────────────
if 'logged' not in st.session_state:
    st.session_state.logged = False
    st.session_state.is_admin = False
    st.session_state.usuario = None

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
            # Obtener lista única de usuarios que han registrado algo
            usuarios_df = pd.read_sql_query("SELECT DISTINCT usuario FROM capturas WHERE usuario IS NOT NULL ORDER BY usuario", conn)
            usuarios = ["Todos"] + usuarios_df['usuario'].tolist()

            # Selector de usuario
            usuario_seleccionado = st.selectbox("Filtrar por usuario que registró", usuarios)

            # Consulta base
            query = "SELECT id, usuario, nombre, seccion, telefono, domicilio, edad FROM capturas"
            params = ()
            if usuario_seleccionado != "Todos":
                query += " WHERE usuario = ?"
                params = (usuario_seleccionado,)

            query += " ORDER BY id DESC"
            df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                st.info("No hay registros para el filtro seleccionado.")
            else:
                st.dataframe(df, use_container_width=True)

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
        st.title("📝 Captura de Datos")
        st.markdown(f"Logueado como: **{st.session_state.usuario}**")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.usuario = None
            st.rerun()

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
                                         (usuario, nombre, seccion, telefono, domicilio, edad)
                                         VALUES (?, ?, ?, ?, ?, ?)''',
                                      (st.session_state.usuario, nombre, seccion, telefono, domicilio, edad))
                            conn.commit()
                        st.success(f"¡Datos guardados por {st.session_state.usuario}! (demo)")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")