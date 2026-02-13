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
                        calle TEXT,
                        numero TEXT,
                        colonia TEXT,
                        cp TEXT,
                        ciudad TEXT,
                        nombre TEXT,
                        apellido_paterno TEXT,
                        apellido_materno TEXT,
                        seccion TEXT,
                        celular TEXT
                     )''')
        conn.commit()

init_db()

# ────────────────────────────────────────────────
# Estado de sesión
# ────────────────────────────────────────────────
if 'logged' not in st.session_state:
    st.session_state.logged = False
    st.session_state.is_admin = False

# ────────────────────────────────────────────────
# Pantalla de login (primera vista)
# ────────────────────────────────────────────────
if not st.session_state.logged:
    st.title("Iniciar Sesión")
    st.markdown("Ingresa tus credenciales para continuar")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("Usuario", placeholder="Ej: admin")
        contraseña = st.text_input("Contraseña", type="password", placeholder="Ej: 1234")

        if st.button("Entrar", type="primary", use_container_width=True):
            if not usuario or not contraseña:
                st.error("Ingresa usuario y contraseña")
            else:
                # Credenciales de demo (cámbialas si quieres)
                if usuario.strip().lower() == "admin" and contraseña == "1234":
                    st.session_state.logged = True
                    st.session_state.is_admin = True
                    st.success("Bienvenido Administrador")
                    st.rerun()
                else:
                    # Cualquier otro usuario válido → modo usuario normal
                    st.session_state.logged = True
                    st.session_state.is_admin = False
                    st.success("Bienvenido Usuario")
                    st.rerun()

else:
    # ────────────────────────────────────────────────
    # Vista según rol
    # ────────────────────────────────────────────────
    if st.session_state.is_admin:
        st.title("🛠 Panel Administrador")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.session_state.is_admin = False
            st.rerun()

        try:
            df = pd.read_sql_query("SELECT * FROM capturas ORDER BY id DESC", get_connection())
            if df.empty:
                st.info("No hay registros aún.")
            else:
                st.dataframe(df, use_container_width=True)

            st.subheader("Eliminar registros")
            ids = st.multiselect("Selecciona los ID a borrar", options=df['id'].tolist())
            if st.button("Borrar seleccionados") and ids:
                with get_connection() as conn:
                    c = conn.cursor()
                    placeholders = ','.join('?' for _ in ids)
                    c.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
                    conn.commit()
                st.success(f"Se eliminaron {len(ids)} registro(s)")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer la base de datos: {e}")

    else:
        st.title("📝 Captura de Datos")
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.rerun()

        with st.form("form_captura", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                calle    = st.text_input("Calle")
                numero   = st.text_input("Número")
                colonia  = st.text_input("Colonia")
                cp       = st.text_input("C.P.")
                ciudad   = st.text_input("Ciudad")
            with col2:
                nombre         = st.text_input("Nombre")
                ap_paterno     = st.text_input("Apellido Paterno")
                ap_materno     = st.text_input("Apellido Materno")
                seccion        = st.text_input("Sección")
                celular        = st.text_input("Celular (10 dígitos)", max_chars=10)

            if st.form_submit_button("Guardar"):
                if not all([calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular]):
                    st.error("Todos los campos son obligatorios")
                elif len(celular) != 10 or not celular.isdigit():
                    st.error("El celular debe tener exactamente 10 dígitos numéricos")
                else:
                    try:
                        with get_connection() as conn:
                            c = conn.cursor()
                            c.execute('''INSERT INTO capturas 
                                         (calle, numero, colonia, cp, ciudad, nombre, apellido_paterno, apellido_materno, seccion, celular)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                      (calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular))
                            conn.commit()
                        st.success("¡Datos guardados correctamente! (solo para esta sesión de demo)")
                        # st.balloons()  ← quitado
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")