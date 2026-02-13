import os
import streamlit as st
import sqlalchemy as sa
from sqlalchemy import text
import pandas as pd

# ────────────────────────────────────────────────
# Configuración básica de la app
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Captura de Datos",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ────────────────────────────────────────────────
# Conexión a la base de datos remota
# ────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("No se encontró la variable DATABASE_URL en las variables de entorno.")
    st.error("Configúrala en Secrets (Streamlit Cloud) o en Environment Variables (Render).")
    st.stop()

# Creamos el engine con opciones recomendadas para Neon / Supabase
engine = sa.create_engine(
    DATABASE_URL,
    connect_args={
        "options": "-csearch_path=public",
        "sslmode": "require"          # fuerza SSL si no está en la URL
    }
)

# ────────────────────────────────────────────────
# Crear tabla si no existe (se ejecuta solo una vez al inicio)
# ────────────────────────────────────────────────
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
                );
            """))
            conn.commit()
            # print("Tabla capturas verificada/creada correctamente")  # descomenta para logs
    except Exception as e:
        st.error(f"Error al crear/verificar la tabla: {str(e)}")
        st.stop()

# Ejecutamos la inicialización (puedes comentarlo después de la primera ejecución)
init_db()

# ────────────────────────────────────────────────
# Sidebar - Selección de rol
# ────────────────────────────────────────────────
st.sidebar.title("Perfil")
rol = st.sidebar.radio("Elige tu rol", ["👤 Usuario", "🛠️ Administrador"])

# ────────────────────────────────────────────────
# Rol: USUARIO - Formulario de captura
# ────────────────────────────────────────────────
if rol == "👤 Usuario":
    st.title("📝 Captura de Datos")
    st.markdown("Completa todos los campos para registrar la información")

    with st.form("form_captura", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            calle    = st.text_input("Calle", key="calle")
            numero   = st.text_input("Número", key="numero")
            colonia  = st.text_input("Colonia", key="colonia")
            cp       = st.text_input("C.P.", key="cp")
            ciudad   = st.text_input("Ciudad", key="ciudad")
        with col2:
            nombre         = st.text_input("Nombre", key="nombre")
            ap_paterno     = st.text_input("Apellido Paterno", key="ap_paterno")
            ap_materno     = st.text_input("Apellido Materno", key="ap_materno")
            seccion        = st.text_input("Sección", key="seccion")
            celular        = st.text_input("Celular (10 dígitos)", max_chars=10, key="celular")

        submitted = st.form_submit_button("Guardar", type="primary", use_container_width=True)

    if submitted:
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
                st.success("¡Datos guardados correctamente!")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar los datos: {str(e)}")

# ────────────────────────────────────────────────
# Rol: ADMINISTRADOR - Login + Tabla + Eliminación
# ────────────────────────────────────────────────
else:
    if 'admin_logged' not in st.session_state:
        st.session_state.admin_logged = False

    if not st.session_state.admin_logged:
        st.title("🔐 Acceso Administrador")
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión", type="primary"):
            # ¡Cambia estas credenciales por algo más seguro en producción!
            if usuario == "admin" and contraseña == "1234":
                st.session_state.admin_logged = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    else:
        st.title("🛠 Panel Administrador")
        if st.button("Cerrar sesión"):
            st.session_state.admin_logged = False
            st.rerun()

        try:
            df = pd.read_sql("SELECT * FROM capturas ORDER BY id DESC", engine)
            
            if df.empty:
                st.info("Aún no hay registros en la base de datos.")
            else:
                st.dataframe(df, use_container_width=True, height=450)

            st.subheader("Eliminar registros")
            ids_a_eliminar = st.multiselect(
                "Selecciona los ID que deseas eliminar",
                options=df["id"].tolist(),
                format_func=lambda x: f"ID {x}"
            )

            if st.button("🗑 Eliminar seleccionados", type="secondary"):
                if not ids_a_eliminar:
                    st.warning("Selecciona al menos un registro")
                else:
                    if st.checkbox(f"Confirmar eliminación de {len(ids_a_eliminar)} registro(s)", value=False):
                        try:
                            with engine.connect() as conn:
                                conn.execute(
                                    text("DELETE FROM capturas WHERE id = ANY(:ids)"),
                                    {"ids": ids_a_eliminar}
                                )
                                conn.commit()
                            st.success(f"Se eliminaron {len(ids_a_eliminar)} registro(s)")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar: {str(e)}")
        except Exception as e:
            st.error(f"No se pudo conectar o leer la base de datos: {str(e)}")
            st.info("Verifica que DATABASE_URL esté correctamente configurada en Secrets / Variables de entorno.")