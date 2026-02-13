import os
import streamlit as st
import sqlalchemy as sa
from sqlalchemy import text
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Captura de Datos", layout="centered")

# ─── CONEXIÓN A BD REMOTA ────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL no está configurada en las variables de entorno de Render.")
    st.error("Ve a Dashboard → tu servicio → Environment → agrega DATABASE_URL con tu cadena de Neon/Supabase.")
    st.stop()

engine = sa.create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}  # obligatorio para Neon/Supabase
)

# Prueba rápida de conexión (sale en logs de Render)
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    st.success("Conexión a BD remota OK (solo ves esto localmente)")
except Exception as e:
    st.error(f"Error de conexión a la BD: {str(e)}")
    st.stop()

# ─── CREAR TABLA SI NO EXISTE ────────────────────────────────────────────
def init_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS capturas (
                    id SERIAL PRIMARY KEY,
                    calle TEXT NOT NULL,
                    numero TEXT NOT NULL,
                    colonia TEXT NOT NULL,
                    cp TEXT NOT NULL,
                    ciudad TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido_paterno TEXT NOT NULL,
                    apellido_materno TEXT NOT NULL,
                    seccion TEXT NOT NULL,
                    celular TEXT NOT NULL
                )
            """))
            conn.commit()
    except Exception as e:
        st.error(f"Error creando tabla: {str(e)}")

init_db()  # Ejecuta una vez (puedes comentarlo después de primer deploy)

# ─── INTERFAZ ─────────────────────────────────────────────────────────────
st.title("Captura de Datos")

rol = st.sidebar.radio("Perfil", ["Usuario", "Administrador"])

if rol == "Usuario":
    st.subheader("Formulario de Captura")

    with st.form("captura_form"):
        col1, col2 = st.columns(2)
        with col1:
            calle = st.text_input("Calle")
            numero = st.text_input("Número")
            colonia = st.text_input("Colonia")
            cp = st.text_input("CP")
            ciudad = st.text_input("Ciudad")
        with col2:
            nombre = st.text_input("Nombre")
            ap_p = st.text_input("Apellido Paterno")
            ap_m = st.text_input("Apellido Materno")
            seccion = st.text_input("Sección")
            celular = st.text_input("Celular (10 dígitos)", max_chars=10)

        if st.form_submit_button("Guardar"):
            if not all([calle, numero, colonia, cp, ciudad, nombre, ap_p, ap_m, seccion, celular]):
                st.error("Completa todos los campos")
            elif len(celular) != 10 or not celular.isdigit():
                st.error("Celular inválido (10 dígitos numéricos)")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO capturas (calle, numero, colonia, cp, ciudad, nombre, apellido_paterno, apellido_materno, seccion, celular)
                            VALUES (:calle, :numero, :colonia, :cp, :ciudad, :nombre, :ap_p, :ap_m, :seccion, :celular)
                        """), {
                            "calle": calle, "numero": numero, "colonia": colonia, "cp": cp, "ciudad": ciudad,
                            "nombre": nombre, "ap_p": ap_p, "ap_m": ap_m, "seccion": seccion, "celular": celular
                        })
                        conn.commit()
                    st.success("Guardado exitosamente!")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")

elif rol == "Administrador":
    st.subheader("Panel Admin")
    # Login simple (cámbialo por algo mejor después)
    if 'logged' not in st.session_state:
        st.session_state.logged = False

    if not st.session_state.logged:
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if user == "admin" and pw == "1234":
                st.session_state.logged = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    else:
        if st.button("Cerrar sesión"):
            st.session_state.logged = False
            st.rerun()

        df = pd.read_sql("SELECT * FROM capturas ORDER BY id DESC", engine)
        st.dataframe(df)

        ids = st.multiselect("IDs a borrar", df['id'].tolist())
        if st.button("Borrar seleccionados") and ids:
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM capturas WHERE id = ANY(:ids)"), {"ids": ids})
                conn.commit()
            st.success(f"Borrados {len(ids)} registros")
            st.rerun()