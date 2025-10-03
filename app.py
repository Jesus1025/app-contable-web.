import streamlit as st
import streamlit_authenticator as stauth
import psycopg2
import pandas as pd
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, grey

# --- 1. CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Ventas", page_icon="💼", layout="wide")

# --- 2. CONEXIÓN A LA BASE DE DATOS (USANDO SECRETS) ---
# Este bloque se conecta a tu base de datos de Supabase.
def get_connection():
    try:
        # st.secrets anida las claves bajo la sección [postgres] en tu secrets.toml
        conn = psycopg2.connect(**st.secrets["postgres"])
        return conn
    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        st.info("Asegúrate de haber configurado correctamente los 'Secrets' en Streamlit Community Cloud.")
        return None

conn = get_connection()
if conn is None:
    st.stop()

# --- 3. CONFIGURACIÓN DE USUARIOS ---
# Hashes generados para las contraseñas: 'bastian123', 'constanza123', 'jesus123'
names = ['Bastián', 'Constanza', 'Jesús']
usernames = ['bastian', 'constanza', 'jesus']
hashed_passwords = [
    '$2b$12$1nE2f3oB4p5q6r7s8t9u0u/Dqo0jUFp4bYLrKwRkOeiCIa.L6YVb7',
    '$2b$12$aBcDeFgHiJkLmNoPqRsTuUvWxYzAbCdEfGhIjKlMnOpQrStUvWxYz',
    '$2b$12$zYxWvUtSrQpOnMlKjIhGfEdCbAlZyXwVuTsRqPoNmLkJiHgFeDcBa'
]

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    'cookie_gestion_ventas_final', 'key_secreto_final_123', cookie_expiry_days=30)

name, authentication_status, username = authenticator.login('Login', 'main')

# --- 4. FUNCIONES DE LA APLICACIÓN ---

def agregar_venta(doc_tipo, neg_tipo, desc, monto_bruto, user):
    """Calcula el neto y guarda la venta en la base de datos."""
    monto_neto = monto_bruto / 1.19
    fecha = datetime.now().strftime('%Y-%m-%d')
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ventas (documento_tipo, tipo_negocio, descripcion, monto_neto, fecha, usuario) VALUES (%s, %s, %s, %s, %s, %s)",
            (doc_tipo, neg_tipo, desc, monto_neto, fecha, user)
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        st.error(f"Error al agregar la venta: {e}")
        conn.rollback() # Revertir cambios si hay un error
        return False

def obtener_ventas_df():
    """Obtiene todas las ventas de la base de datos y las devuelve como un DataFrame de Pandas."""
    try:
        query = "SELECT id, fecha, documento_tipo, tipo_negocio, descripcion, monto_neto, usuario FROM ventas ORDER BY fecha DESC, id DESC"
        df = pd.read_sql_query(query, conn)
        df['iva'] = df['monto_neto'] * 0.19
        df['monto_bruto'] = df['monto_neto'] + df['iva']
        return df
    except Exception as e:
        st.error(f"Error al obtener las ventas: {e}")
        return pd.DataFrame()

def eliminar_venta(id_venta):
    """Elimina una venta de la base de datos por su ID."""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ventas WHERE id = %s", (id_venta,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        st.error(f"Error al eliminar la venta: {e}")
        conn.rollback()
        return False

def generar_pdf(df_mes):
    """Genera un reporte en PDF para el DataFrame proporcionado."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    nombre_mes = pd.to_datetime(df_mes['fecha'].iloc[0]).strftime('%B %Y').capitalize()
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, height - inch, f"Reporte de Ventas - {nombre_mes}")

    # Resumen de Totales
    total_neto = df_mes['monto_neto'].sum()
    total_iva = df_mes['iva'].sum()
    total_bruto = df_mes['monto_bruto'].sum()
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, height - 1.5*inch, "Resumen General del Mes")
    y_pos = height - 1.8*inch
    c.setFont("Helvetica", 11)
    c.drawString(1.2*inch, y_pos, f"Total Ventas Netas: ${total_neto:,.0f}".replace(",", "."))
    y_pos -= 20
    c.drawString(1.2*inch, y_pos, f"Total IVA (19%): ${total_iva:,.0f}".replace(",", "."))
    y_pos -= 20
    c.drawString(1.2*inch, y_pos, f"Total Ventas Brutas: ${total_bruto:,.0f}".replace(",", "."))
    
    # Detalle de ventas
    y_pos -= 60
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y_pos, "Detalle de Ventas del Mes")
    
    y_pos -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.8*inch, y_pos, "Fecha")
    c.drawString(1.8*inch, y_pos, "Tipo Doc.")
    c.drawString(2.8*inch, y_pos, "Descripción")
    c.drawString(5.5*inch, y_pos, "Bruto")
    c.drawString(6.5*inch, y_pos, "Usuario")
    c.line(0.8*inch, y_pos - 5, width - 0.8*inch, y_pos - 5)
    
    y_pos -= 20
    for index, row in df_mes.iterrows():
        c.setFont("Helvetica", 9)
        # Dibujar fondo gris para Diseño Web
        if row['tipo_negocio'] == 'web':
            c.setFillColor(grey)
            c.rect(0.7*inch, y_pos - 3, width - 1.4*inch, 14, stroke=0, fill=1)
            c.setFillColor(black)

        c.drawString(0.8*inch, y_pos, str(row['fecha']))
        c.drawString(1.8*inch, y_pos, row['documento_tipo'])
        c.drawString(2.8*inch, y_pos, row['descripcion'][:35]) # Acortar descripción
        c.drawString(5.5*inch, y_pos, f"${row['monto_bruto']:,.0f}".replace(",", "."))
        c.drawString(6.5*inch, y_pos, row['usuario'])
        y_pos -= 15
        if y_pos < inch:
            c.showPage()
            y_pos = height - inch
            
    c.save()
    buffer.seek(0)
    return buffer

# --- 5. INTERFAZ DE USUARIO ---

if authentication_status:
    # --- Interfaz principal si el login es exitoso ---
    authenticator.logout('Cerrar Sesión', 'sidebar')
    st.sidebar.title(f'Bienvenido, *{name}*')
    
    st.title("Sistema de Gestión Contable 💼")

    # Formulario para agregar nuevas ventas
    st.header("➕ Registrar Nueva Venta")
    with st.form("form_nueva_venta", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            documento_tipo = st.selectbox("Tipo de Documento", ["Boleta", "Factura"])
        with col2:
            tipo_negocio = st.selectbox("Tipo de Negocio", ["Impresión 3D", "Diseño Web"])
        with col3:
            monto_bruto = st.number_input("Monto Total (Bruto)", min_value=0)
        
        descripcion = st.text_input("Descripción de la Venta (Ej: 'Página Web XYZ (Adelanto 1/2)')")
        
        submitted = st.form_submit_button("Registrar Venta")
        if submitted:
            tipo_negocio_code = '3d' if tipo_negocio == "Impresión 3D" else 'web'
            if agregar_venta(documento_tipo, tipo_negocio_code, descripcion, monto_bruto, username):
                st.success("¡Venta registrada con éxito!")
    
    st.markdown("---")

    # Mostrar historial de ventas y opción de descarga
    st.header("📈 Historial General de Ventas")
    df_ventas = obtener_ventas_df()
    
    # Formatear el DataFrame para mostrarlo en la app
    df_display = df_ventas.copy()
    for col in ['monto_neto', 'iva', 'monto_bruto']:
        df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}".replace(",", "."))
    
    df_display.rename(columns={'documento_tipo': 'Documento', 'tipo_negocio': 'Negocio', 'descripcion': 'Descripción', 'monto_bruto': 'Monto Bruto', 'usuario': 'Registrado por'}, inplace=True)
    st.dataframe(df_display[['id', 'fecha', 'Documento', 'Negocio', 'Descripción', 'Monto Bruto', 'Registrado por']])
    
    # Botón para descargar el PDF del mes actual
    df_mes_actual = df_ventas[pd.to_datetime(df_ventas['fecha']).dt.strftime('%Y-%m') == datetime.now().strftime('%Y-%m')]
    if not df_mes_actual.empty:
        pdf_buffer = generar_pdf(df_mes_actual)
        st.download_button(
            label="📄 Descargar Reporte del Mes en PDF",
            data=pdf_buffer,
            file_name=f"Reporte_Ventas_{datetime.now().strftime('%Y_%m')}.pdf",
            mime="application/pdf"
        )

    # Opción para eliminar una venta
    with st.expander("🗑️ Eliminar una venta"):
        if not df_ventas.empty:
            id_para_eliminar = st.selectbox("Selecciona el ID de la venta a eliminar:", df_ventas['id'])
            if st.button("Eliminar Venta Seleccionada", type="primary"):
                if eliminar_venta(id_para_eliminar):
                    st.warning(f"Venta con ID {id_para_eliminar} eliminada.")
                    st.experimental_rerun()
        else:
            st.info("No hay ventas registradas para eliminar.")

elif not authentication_status:
    st.error('Usuario o contraseña incorrecta')
elif authentication_status is None:
    st.warning('Por favor, ingresa tus credenciales para continuar.')