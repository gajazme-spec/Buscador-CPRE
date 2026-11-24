import io
import re
import pandas as pd
import streamlit as st

try:
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

st.set_page_config(page_title="Extractor Base CPRE", layout="wide")

PATRONES_CPRE = [
    r"\bCPRE\b", r"colangiopancreatograf[ií]a", r"canalizaci[oó]n\s+biliar",
    r"papilotom[ií]a", r"pr[oó]tesis\s+biliar", r"recambio\s+de\s+pr[oó]tesis",
    r"colangiocarcinoma", r"colestasis", r"coledocolitiasis", r"fuga\s+biliar",
    r"ictericia\s+obstructiva", r"estenosis\s+biliar", r"dilataci[oó]n\s+biliar"
]
REGEX_CPRE = re.compile("|".join(PATRONES_CPRE), re.IGNORECASE)
REGEX_EXP = re.compile(r"\b(FOL\d+|\d{6,9})\b", re.IGNORECASE)
REGEX_EDAD_GEN = re.compile(r"\b([MF])\s*(\d{2})\b|\b(\d{2})a\.\s*([MF])\b", re.IGNORECASE)
REGEX_HB = re.compile(r"\b(?:HB|Hb|Hemoglobina)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
REGEX_PLT = re.compile(r"\b(?:PLT|Plt|Plaquetas|Plaq|PIt)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
REGEX_ALB = re.compile(r"\b(?:ALB|Alb|Albúmina)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
REGEX_BT = re.compile(r"\b(?:BT|Bt|Bilirrubina\s+Total)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
REGEX_CREAT = re.compile(r"\b(?:CR|Cr|Creatinina)\s*[:=]?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

def extraer_datos_paciente(linea):
    datos = {
        "Expediente": "", "Género": "", "Edad actual": "",
        "HB": "", "PLT": "", "ALB": "", "BT": "", "Cr": ""
    }
    
    m_exp = REGEX_EXP.search(linea)
    if m_exp: datos["Expediente"] = m_exp.group(1)
    
    m_edad_gen = REGEX_EDAD_GEN.search(linea)
    if m_edad_gen:
        if m_edad_gen.group(1):
            datos["Género"] = "Masculino" if m_edad_gen.group(1).upper() == "M" else "Femenino"
            datos["Edad actual"] = m_edad_gen.group(2)
        elif m_edad_gen.group(3):
            datos["Edad actual"] = m_edad_gen.group(3)
            datos["Género"] = "Masculino" if m_edad_gen.group(4).upper() == "M" else "Femenino"

    m_hb = REGEX_HB.search(linea)
    if m_hb: datos["HB"] = m_hb.group(1)
    
    m_plt = REGEX_PLT.search(linea)
    if m_plt: datos["PLT"] = m_plt.group(1)
    
    m_alb = REGEX_ALB.search(linea)
    if m_alb: datos["ALB"] = m_alb.group(1)
    
    m_bt = REGEX_BT.search(linea)
    if m_bt: datos["BT"] = m_bt.group(1)
    
    m_creat = REGEX_CREAT.search(linea)
    if m_creat: datos["Cr"] = m_creat.group(1)

    return datos

def escanear_pdf(contenido, nombre):
    if not PDF_OK: return []
    resultados = []
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        texto_total = ""
        for pagina in pdf.pages:
            texto_total += (pagina.extract_text() or "") + "\n"
    
    lineas = texto_total.splitlines()
    for linea in lineas:
        if REGEX_CPRE.search(linea):
            datos = extraer_datos_paciente(linea)
            if datos["Expediente"]:
                datos["Origen"] = nombre
                resultados.append(datos)
    return resultados

st.title("Generador de Base de Datos CPRE")
st.caption("Sube el PDF del censo. Extraerá expedientes de CPRE y sus laboratorios automáticamente.")

if not PDF_OK:
    st.error("Falta pdfplumber. Ejecuta: py -m pip install pdfplumber")

archivo = st.file_uploader("Sube el PDF del censo", type=["pdf"])

if archivo:
    with st.spinner("Extrayendo datos del PDF..."):
        resultados = escanear_pdf(archivo.getvalue(), archivo.name)
        
    if resultados:
        df = pd.DataFrame(resultados)
        df_uniq = df.drop_duplicates(subset=["Expediente"], keep="first")
        
        columnas_orden = ["Expediente", "Género", "Edad actual", "HB", "PLT", "ALB", "BT", "Cr", "Origen"]
        columnas_existentes = [c for c in columnas_orden if c in df_uniq.columns]
        df_final = df_uniq[columnas_existentes]

        st.success(f"¡Se encontraron {len(df_final)} pacientes con CPRE!")
        st.dataframe(df_final, width='stretch', hide_index=True)

        buf = io.BytesIO()
        df_final.to_excel(buf, index=False)
        st.download_button(
            label="⬇️ Descargar Base de Datos en Excel",
            data=buf.getvalue(),
            file_name="Base_CPRE_Extraida.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("No se encontraron pacientes de CPRE en el PDF.")
