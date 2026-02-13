import streamlit as st
import sqlite3
import pandas as pd
import os

# Configuración de página
st.set_page_config(page_title="Captura de Datos", layout="wide")

# Ruta al archivo SQLite en el disco persistente de Render
# Usa la ruta que configures en Render Disks (ejemplo común)
DB_PATH = "/data/datos.db"  # Cambia a la ruta que pongas en Render (ej: /var/data/datos.db o /opt/render/project/src/datos.db)

# Crea el directorio si no existe (Render permite escritura en el mount path)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Conexión a SQLite
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Para retornar filas como dict
    return conn

# Inicializar tabla (se ejecuta al inicio)
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

# Sidebar para seleccionar rol
rol = st.sidebar.radio("Perfil", ["Usuario", "Administrador"])

# Rol: Usuario - Formulario de captura
if rol == "Usuario":
    st.title("Captura de Datos")

    with st.form("captura_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            calle = st.text_input("Calle")
            numero = st.text_input("Número")
            colonia = st.text_input("Colonia")
            cp = st.text_input("C.P.")
            ciudad = st.text_input("Ciudad")
        with col2:
            nombre = st.text_input("Nombre")
            ap_paterno = st.text_input("Apellido Paterno")
            ap_materno = st.text_input("Apellido Materno")
            seccion = st.text_input("Sección")
            celular = st.text_input("Celular (10 dígitos)", max_chars=10)

        if st.form_submit_button("Guardar"):
            if not all([calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular]):
                st.error("Completa todos los campos")
            elif len(celular) != 10 or not celular.isdigit():
                st.error("Celular debe tener 10 dígitos numéricos")
            else:
                try:
                    with get_connection() as conn:
                        c = conn.cursor()
                        c.execute('''INSERT INTO capturas 
                                     (calle, numero, colonia, cp, ciudad, nombre, apellido_paterno, apellido_materno, seccion, celular)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular))
                        conn.commit()
                    st.success("¡Guardado correctamente!")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# Rol: Administrador - Login + Tabla + Borrar
else:
    st.title("Panel Administrador")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            # Cambia esto por credenciales seguras (o usa st.secrets)
            if usuario == "admin" and contraseña == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    else:
        if st.button("Cerrar sesión"):
            st.session_state.logged_in = False
            st.rerun()

        try:
            df = pd.read_sql_query("SELECT * FROM capturas ORDER BY id DESC", get_connection())
            if df.empty:
                st.info("No hay registros aún.")
            else:
                st.dataframe(df, use_container_width=True)

            st.subheader("Eliminar registros")
            ids = st.multiselect("Selecciona IDs", options=df['id'].tolist())
            if st.button("Borrar seleccionados") and ids:
                with get_connection() as conn:
                    c = conn.cursor()
                    placeholders = ','.join('?' * len(ids))
                    c.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
                    conn.commit()
                st.success(f"Eliminados {len(ids)} registros")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer la base: {e}")