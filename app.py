import streamlit as st
import sqlite3
import pandas as pd
import os

# ────────────────────────────────────────────────
# Configuración de la app
# ────────────────────────────────────────────────
st.set_page_config(page_title="Captura de Datos", layout="wide")

# Ruta al archivo SQLite en el disco persistente
# Render monta el disco en /data o la ruta que configures
DB_PATH = "/opt/render/project/src/datos.db"  # Cambia según tu mount path en Render

# Crea carpeta si no existe (por si acaso)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ────────────────────────────────────────────────
# Conexión y creación de tabla
# ────────────────────────────────────────────────
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Para retornar dicts
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

init_db()  # Ejecuta al inicio

# ────────────────────────────────────────────────
# Sidebar para roles
# ────────────────────────────────────────────────
st.sidebar.title("Perfil")
rol = st.sidebar.radio("Selecciona:", ["Usuario", "Administrador"])

# ────────────────────────────────────────────────
# Rol Usuario: Formulario
# ────────────────────────────────────────────────
if rol == "Usuario":
    st.title("📝 Captura de Datos")

    with st.form("form_captura", clear_on_submit=True):
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

        submitted = st.form_submit_button("Guardar", type="primary")

    if submitted:
        if not all([calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular]):
            st.error("Todos los campos son obligatorios")
        elif len(celular) != 10 or not celular.isdigit():
            st.error("Celular inválido (10 dígitos numéricos)")
        else:
            try:
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute('''INSERT INTO capturas 
                                 (calle, numero, colonia, cp, ciudad, nombre, apellido_paterno, apellido_materno, seccion, celular)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular))
                    conn.commit()
                st.success("¡Datos guardados correctamente!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ────────────────────────────────────────────────
# Rol Administrador: Login + Tabla + Borrar
# ────────────────────────────────────────────────
else:
    st.title("🛠 Panel Administrador")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            # ¡Cambia esto por credenciales seguras!
            if usuario == "admin" and contraseña == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    else:
        if st.button("Cerrar sesión"):
            st.session_state.logged_in = False
            st.rerun()

        # Mostrar tabla
        try:
            df = pd.read_sql_query("SELECT * FROM capturas ORDER BY id DESC", get_connection())
            if df.empty:
                st.info("No hay registros aún")
            else:
                st.dataframe(df, use_container_width=True)

            # Borrar
            st.subheader("Eliminar registros")
            ids = st.multiselect("Selecciona IDs", df['id'].tolist())
            if st.button("Borrar seleccionados") and ids:
                with get_connection() as conn:
                    c = conn.cursor()
                    placeholders = ','.join('?' for _ in ids)
                    c.execute(f"DELETE FROM capturas WHERE id IN ({placeholders})", ids)
                    conn.commit()
                st.success(f"Eliminados {len(ids)} registros")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer la base: {e}")