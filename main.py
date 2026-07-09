import streamlit as st
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import io
import pandas as pd
import os
import barcode
from barcode.writer import ImageWriter

# Configuração de Layout
st.set_page_config(page_title="Gerador de Etiquetas", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #f0f8ff; }
    h1 { color: #004e92; text-align: center; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_dados():
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, 'estoque.csv')
    return pd.read_csv(caminho, sep=';', header=None, skiprows=1, usecols=[1, 2, 3, 6], 
                       names=['nome', 'codigo', 'categoria', 'quantidade'], engine='python', on_bad_lines='skip')

def gerar_pdf_etiqueta(nome, codigo, categoria, qtd):
    # Gerar código de barras temporário
    code128 = barcode.get('code128', str(codigo), writer=ImageWriter())
    code128.save('temp_barcode', options={"write_text": False, "module_width": 0.2, "module_height": 5.0})

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(70*mm, 50*mm))
    c.rect(2*mm, 2*mm, 66*mm, 46*mm)
    c.line(2*mm, 25*mm, 68*mm, 25*mm)
    
    try: c.drawImage("download.png", 5*mm, 28*mm, width=20*mm, height=18*mm, preserveAspectRatio=True)
    except: pass
    
    cat_texto = categoria if categoria != "N/A" else ""
    estilo = ParagraphStyle('nome', fontSize=9, leading=10)
    p_nome = Paragraph(f"<b>{nome}</b><br/><font size=7>{cat_texto}</font>", estilo)
    p_nome.wrapOn(c, 40*mm, 20*mm)
    p_nome.drawOn(c, 28*mm, 32*mm)
    
    estilo_inf = ParagraphStyle('inf', fontSize=9, leading=10)
    p_info = Paragraph(f"REF: <b>{codigo}</b><br/>FABRICADO NO BRASIL", estilo_inf)
    p_info.wrapOn(c, 60*mm, 20*mm)
    p_info.drawOn(c, 5*mm, 15*mm)

    # Inserir Código de Barras
    c.drawImage('temp_barcode.png', 10*mm, 5*mm, width=50*mm, height=10*mm)
    
    c.showPage(); c.save()
    return buffer.getvalue()

st.title("🏷️ Gerador de Etiquetas")
aba1, aba2 = st.tabs(["📄 Ler XML NFe", "📦 Consulta Manual"])

with aba1:
    uploaded_file = st.file_uploader("Upload XML", type="xml")
    if uploaded_file:
        root = ET.parse(uploaded_file).getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        for det in root.findall('.//nfe:det', ns):
            prod = det.find('nfe:prod', ns)
            nome = prod.find('nfe:xProd', ns).text
            cod = prod.find('nfe:cProd', ns).text
            st.write(f"**{nome}**")
            if st.button("Gerar Etiqueta", key=f"xml_{cod}"):
                st.download_button("Baixar PDF", data=gerar_pdf_etiqueta(nome, cod, "", 1), file_name=f"{cod}.pdf")

with aba2:
    df = carregar_dados()
    col_a, col_b = st.columns(2)
    with col_a: filtro_cat = st.multiselect("Família:", df['categoria'].unique().tolist())
    with col_b: busca = st.text_input("Buscar nome:")
    
    df_f = df
    if filtro_cat: df_f = df_f[df_f['categoria'].isin(filtro_cat)]
    if busca: df_f = df_f[df_f['nome'].str.contains(busca, case=False, na=False)]
    
    for _, p in df_f.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{p['nome']}**")
            qtd = c2.number_input("Qtd", value=int(float(str(p['quantidade']).replace(',','.'))), key=f"q_{p['codigo']}")
            if c3.button("Imprimir", key=f"btn_{p['codigo']}"):
                pdf = gerar_pdf_etiqueta(p['nome'], str(p['codigo']), str(p['categoria']), qtd)
                st.download_button("Baixar PDF", data=pdf, file_name=f"{p['codigo']}.pdf", mime="application/pdf")