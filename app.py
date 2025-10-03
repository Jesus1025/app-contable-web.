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

# --- 2. CONEXIÓN A LA BASE DE DATOS ---
def get_connection():
    try:
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
config = {
    "credentials": {
        "usernames": {
            "bastian": {
                "name": "Bastián",
                "password": '$2b$12$1nE2f3oB4p5q6r7s8t9u0u/Dqo0jUFp4bYLrKwRkOeiCIa.L6YVb7'
            },
            "constanza": {
                "name": "Constanza",
                "password": '$2b$12$aBcDeFgHiJkLmNoPqRsTuUvWxYzAbCdEfGhIjKlMnOpQrStUvWxYz'
            },
            "jesus": {
                "name": "Jesús",
                "password": '$2b$12$zYxWvUtSrQpOnMlKjIhGfEdCbAlZyXwVuTsRqPoNmLkJiHgFeDcBa'
            }
        }
    },
    "cookie": {
        "name": "cookie_gestion_ventas_final",
        "key": "key_secreto_final_123",
        "expiry_days": 30
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- 4. FUNCIONES DE LA APLICACIÓN ---
def agregar_venta(doc_tipo, neg_tipo, desc, monto_bruto, user):
    monto_neto = monto_bruto / 1.19
    fecha = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ventas (documento_tipo, tipo_negocio, descripcion, monto_neto, fecha, usuario) VALUES (%s, %s, %s, %s, %s, %s)",
        (doc_tipo, neg_tipo, desc, monto_neto, fecha, user)
    )
    conn.commit()
    cursor.close()

def obtener_ventas_df():
    query = "SELECT id, fecha, documento_tipo, tipo_negocio, descripcion, monto_neto, usuario FROM ventas ORDER BY fecha DESC, id DESC"
    df = pd.read_sql_query(query, conn)
    df['iva'] = df['monto_neto'] * 0.19
    df['monto_bruto'] = df['monto_neto'] + df['iva']
    return df

def eliminar_venta(id_venta):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ventas WHERE id = %s", (id_venta,))
    conn.commit()
    cursor.close()

def generar_pdf(df_mes):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    nombre_mes = pd.to_datetime(df_mes['fecha'].iloc[0]).strftime('%B %Y').capitalize()
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, height - inch, f"Reporte de Ventas - {nombre_mes}")

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
        if row['tipo_negocio'] == 'web':
            c.setFillColor(grey)
            c.rect(0.7*inch, y_pos - 3, width - 1.4*inch, 14, stroke=0, fill=1)
            c.setFillColor(black)

        c.drawString(0.8*inch, y_pos, str(row['fecha']))
        c.drawString(1.8*inch, y_pos, row['documento_tipo'])
        c.drawString(2.8*inch, y_pos, row['descripcion'][:35])
        c.drawString(5.5*inch, y_pos, f"${row['monto_bruto']:,.0f}".replace(",", "."))
        c.drawString(6.5*inch, y_pos, row['usuario'])
        y_pos -= 15
        if y_pos < inch:
            c.showPage()
            y_pos = height - inch
            
    c.save()
    buffer.seek(0)
    return buffer

# --- 5. INTERFAZ DE USUARIO (LA LÍNEA CORREGIDA) ---
authenticator.login() # <-- ¡ESTA ES LA LÍNEA CORREGIDA!

if st.session_state["authentication_status"]:
    authenticator.logout('Cerrar Sesión', location='sidebar') # Se agrega 'location'
    st.sidebar.title(f'Bienvenido, *{st.session_state["name"]}*')
    
    st.title("Sistema de Gestión Contable 💼")

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
            if agregar_venta(documento_tipo, tipo_negocio_code, descripcion, monto_bruto, st.session_state["username"]):
                st.success("¡Venta registrada con éxito!")
    
    st.markdown("---")

    st.header("📈 Historial General de Ventas")
    df_ventas = obtener_ventas_df()
    
    df_display = df_ventas.copy()
    for col in ['monto_neto', 'iva', 'monto_bruto']:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.0f}".replace(",", "."))
    
    df_display.rename(columns={'documento_tipo': 'Documento', 'tipo_negocio': 'Negocio', 'descripcion': 'Descripción', 'monto_bruto': 'Monto Bruto', 'usuario': 'Registrado por'}, inplace=True)
    st.dataframe(df_display[['id', 'fecha', 'Documento', 'Negocio', 'Descripción', 'Monto Bruto', 'Registrado por']])
    
    df_mes_actual = df_ventas[pd.to_datetime(df_ventas['fecha']).dt.strftime('%Y-%m') == datetime.now().strftime('%Y-%m')]
    if not df_mes_actual.empty:
        pdf_buffer = generar_pdf(df_mes_actual)
        st.download_button(
            label="📄 Descargar Reporte del Mes en PDF",
            data=pdf_buffer,
            file_name=f"Reporte_Ventas_{datetime.now().strftime('%Y_%m')}.pdf",
            mime="application/pdf"
        )

    with st.expander("🗑️ Eliminar una venta"):
        if not df_ventas.empty:
            id_para_eliminar = st.selectbox("Selecciona el ID de la venta a eliminar:", df_ventas['id'])
            if st.button("Eliminar Venta Seleccionada", type="primary"):
                if eliminar_venta(id_para_eliminar):
                    st.warning(f"Venta con ID {id_para_eliminar} eliminada.")
                    st.experimental_rerun()
        else:
            st.info("No hay ventas registradas para eliminar.")

elif st.session_state["authentication_status"] == False:
    st.error('Usuario o contraseña incorrecta')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, ingresa tus credenciales para continuar.')
