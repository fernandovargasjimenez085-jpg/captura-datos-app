import streamlit as st
import sqlalchemy as sa
from sqlalchemy import text
import pandas as pd
import os

# ────────────────────────────────────────────────
#  Configuración
# ────────────────────────────────────────────────

st.set_page_config(
    page_title="Captura de Datos",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Cambia esto por tu cadena real de Supabase (o Neon, etc.)
# Formato: postgresql://user:password@host:port/dbname?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:tucontraseña@localhost:5432/postgres")

# Si no hay variable de entorno → modo desarrollo local (cambia a tu local si quieres)
if "localhost" in DATABASE_URL:
    st.warning("Usando base de datos local de desarrollo. En producción configura DATABASE_URL.")

# ────────────────────────────────────────────────
# Conexión a la base de datos
# ────────────────────────────────────────────────

@st.cache_resource
def get_engine():
    return sa.create_engine(DATABASE_URL, connect_args={"options": "-csearch_path=public"})

engine = get_engine()

# Crear tabla si no existe
def init_db():
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
            );
        """))
        conn.commit()

init_db()

# ────────────────────────────────────────────────
# Sidebar - Selección de rol
# ────────────────────────────────────────────────

st.sidebar.title("Perfil")
rol = st.sidebar.radio("Elige tu rol", ["👤 Usuario", "🛠️ Administrador"])

# ────────────────────────────────────────────────
# Usuario: Formulario de captura
# ────────────────────────────────────────────────

if rol == "👤 Usuario":
    st.title("📝 Captura de Datos")
    st.markdown("Completa todos los campos")

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

        guardar = st.form_submit_button("Guardar", type="primary", use_container_width=True)

    if guardar:
        if not all([calle, numero, colonia, cp, ciudad, nombre, ap_paterno, ap_materno, seccion, celular]):
            st.error("Todos los campos son obligatorios")
        elif len(celular) != 10 or not celular.isdigit():
            st.error("El celular debe tener exactamente 10 dígitos numéricos")
        else:
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        INSERT INTO capturas (
                            calle, numero, colonia, cp, ciudad,
                            nombre, apellido_paterno, apellido_materno, seccion, celular
                        ) VALUES (
                            :calle, :numero, :colonia, :cp, :ciudad,
                            :nombre, :apellido_paterno, :apellido_materno, :seccion, :celular
                        )
                    """), {
                        "calle": calle, "numero": numero, "colonia": colonia, "cp": cp, "ciudad": ciudad,
                        "nombre": nombre, "apellido_paterno": ap_paterno, "apellido_materno": ap_materno,
                        "seccion": seccion, "celular": celular
                    })
                    conn.commit()
                st.success("¡Datos guardados exitosamente!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")

# ────────────────────────────────────────────────
# Administrador: Login + Tabla + Borrar
# ────────────────────────────────────────────────

else:
    if 'admin_logged' not in st.session_state:
        st.session_state.admin_logged = False

    if not st.session_state.admin_logged:
        st.title("🔐 Acceso Administrador")
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión", type="primary"):
            if usuario == "admin" and contraseña == "1234":  # ¡cambia esto en producción!
                st.session_state.admin_logged = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    else:
        st.title("🛠 Panel Administrador")
        if st.button("Cerrar sesión"):
            st.session_state.admin_logged = False
            st.rerun()

        # Cargar datos
        try:
            df = pd.read_sql("SELECT * FROM capturas ORDER BY id DESC", engine)
            st.dataframe(df, use_container_width=True, height=450)

            st.subheader("Eliminar registros")
            ids_a_borrar = st.multiselect(
                "Selecciona ID(s) a eliminar",
                options=df["id"].tolist(),
                format_func=lambda x: f"ID {x}"
            )

            if st.button("🗑 Eliminar seleccionados", type="secondary"):
                if not ids_a_borrar:
                    st.warning("Selecciona al menos un registro")
                else:
                    with st.spinner("Eliminando..."):
                        with engine.connect() as conn:
                            conn.execute(
                                text("DELETE FROM capturas WHERE id = ANY(:ids)"),
                                {"ids": ids_a_borrar}
                            )
                            conn.commit()
                    st.success(f"Eliminados {len(ids_a_borrar)} registro(s)")
                    st.rerun()
        except Exception as e:
            st.error(f"Error al conectar/leer la base de datos:\n{str(e)}")
            st.info("Verifica que DATABASE_URL esté bien configurada en las variables de entorno de Render.")