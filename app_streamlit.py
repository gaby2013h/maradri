##############################################
# Agente Economico De IA                     #
# Interfaz visual (chat en HTML) con Streamlit #
##############################################
# Para ejecutarlo, en la terminal (con el ambiente activado):
#     python -m streamlit run app_streamlit.py

import requests
import pandas as pd
import streamlit as st

# Reutilizamos el agente que YA funciona (cerebro + herramientas), sin modificarlo
from agente_economico import client, process_response, MEMORY_MAX_MESSAGES


# ---------- Personalizacion (cambia aqui el nombre y el color) ----------
NOMBRE_AGENTE = "MARADRI"
DESCRIPCION = "Datos Económicos para Ti"
COLOR_PRINCIPAL = "#C2185B"   # rosa frambuesa (titulos)
COLORES_GRAFICA = ["#D63384", "#9C6ADE", "#F48FB1", "#7B3F61", "#E6A0C4", "#B39DDB", "#AD1457"]
AVATAR_AGENTE = "🌸"
AVATAR_USUARIA = "👩"


# ---------- Configuracion de la pagina ----------
st.set_page_config(page_title=NOMBRE_AGENTE, page_icon="🌸", layout="wide")

st.markdown(
    f"""
    <style>
    h1, h2, h3 {{ color: {COLOR_PRINCIPAL}; }}
    [data-testid="stChatMessage"] {{ border-radius: 16px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Datos para las graficas (Banco Mundial, ultimos 10 años) ----------
INDICADORES = {
    "PIB (USD corrientes)": "NY.GDP.MKTP.CD",
    "Inflación (% anual)": "FP.CPI.TOTL.ZG",
    "Desempleo (% fuerza laboral)": "SL.UEM.TOTL.ZS",
    "Balanza comercial de bienes (USD)": "BN.GSR.MRCH.CD",
    "Subalimentación (% población)": "SN.ITK.DEFC.ZS",
}

PAISES = {
    "Guatemala": "GTM",
    "El Salvador": "SLV",
    "Honduras": "HND",
    "Nicaragua": "NIC",
    "Costa Rica": "CRI",
    "México": "MEX",
    "Estados Unidos": "USA",
}


@st.cache_data(ttl=3600)  # guarda el resultado 1 hora para no consultar la API cada vez
def serie_historica(codigo_pais: str, indicador: str):
    url = f"https://api.worldbank.org/v2/country/{codigo_pais}/indicator/{indicador}"
    respuesta = requests.get(url, params={"format": "json", "mrv": 10}, timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, list) or len(datos) < 2 or not datos[1]:
        return pd.DataFrame()
    filas = [(int(r["date"]), r["value"]) for r in datos[1] if r["value"] is not None]
    return pd.DataFrame(filas, columns=["Año", "Valor"]).sort_values("Año").set_index("Año")


# ---------- Barra lateral ----------
with st.sidebar:
    st.title(f"🌸 {NOMBRE_AGENTE}")
    st.caption(DESCRIPCION)

    st.subheader("💡 ¿Qué puedo hacer?")
    st.markdown(
        "- PIB e inflación\n"
        "- Tipo de cambio\n"
        "- Desempleo\n"
        "- Balanza comercial\n"
        "- Subalimentación\n"
        "- Comparar países"
    )

    st.subheader("📈 Gráfica de indicadores")
    indicador_elegido = st.selectbox("Indicador", list(INDICADORES.keys()))
    paises_elegidos = st.multiselect("Países", list(PAISES.keys()), default=["Guatemala"])

    if st.button("🗑️ Borrar conversación"):
        st.session_state.mensajes = []
        st.rerun()


# ---------- Encabezado ----------
st.title(f"💬 {NOMBRE_AGENTE}")
st.caption("Pregúntame sobre la economía de Guatemala y la región. Datos del Banco Mundial y open.er-api.com.")


# ---------- Grafica (segun lo elegido en la barra lateral) ----------
if paises_elegidos:
    with st.expander(f"📈 {indicador_elegido} – últimos 10 años", expanded=False):
        try:
            columnas = {}
            for nombre in paises_elegidos:
                serie = serie_historica(PAISES[nombre], INDICADORES[indicador_elegido])
                if not serie.empty:
                    columnas[nombre] = serie["Valor"]
            tabla = pd.concat(columnas, axis=1) if columnas else pd.DataFrame()
            if tabla.empty:
                st.info("No hay datos disponibles para esa selección.")
            else:
                st.line_chart(tabla, color=COLORES_GRAFICA[: len(tabla.columns)])
                st.caption("Fuente: Banco Mundial")
        except Exception as e:
            st.error(f"No se pudo cargar la gráfica: {e}")


# ---------- MEMORIA: Streamlit vuelve a correr el archivo en cada interaccion, ----------
# ---------- por eso la conversacion se guarda en st.session_state             ----------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar la conversacion guardada
for m in st.session_state.mensajes:
    with st.chat_message(m["role"], avatar=AVATAR_USUARIA if m["role"] == "user" else AVATAR_AGENTE):
        st.markdown(m["content"])

# Mensaje de bienvenida si aun no hay conversacion
if not st.session_state.mensajes:
    with st.chat_message("assistant", avatar=AVATAR_AGENTE):
        st.markdown(
            f"¡Hola! Soy **{NOMBRE_AGENTE}**. Puedes preguntarme, por ejemplo:\n"
            "- ¿Cuál es la inflación de Guatemala?\n"
            "- ¿A cuánto está el dólar?\n"
            "- Compara el desempleo de Guatemala y Honduras"
        )


# ---------- Caja de texto del chat ----------
pregunta = st.chat_input("Escribe tu pregunta o solicitud...")

if pregunta:
    with st.chat_message("user", avatar=AVATAR_USUARIA):
        st.markdown(pregunta)

    # Solo se envian los ultimos mensajes, igual que la memoria basica del agente
    memoria = st.session_state.mensajes[-MEMORY_MAX_MESSAGES:]

    with st.chat_message("assistant", avatar=AVATAR_AGENTE):
        with st.spinner("Consultando datos..."):
            try:
                respuesta = process_response(client, memoria, pregunta)
            except Exception as e:
                respuesta = f"⚠️ Ocurrió un error al consultar el agente: {e}"
        st.markdown(respuesta)

    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
