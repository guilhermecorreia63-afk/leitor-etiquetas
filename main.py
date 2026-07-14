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

st.set_page_config(page_title="Gerador de Etiquetas", layout="wide")

def carregar_dados():
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, 'estoque.csv')
    df = pd.read_csv(caminho, sep=';')
    df.columns = df.columns.str.strip()
    # Limpeza de números
    df['Estoque Físico'] = pd.to_numeric(df['Estoque Físico'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    return df

def gerar_pdf_etiquetas_multiplas(lista_produtos):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(70*mm, 50*mm))
    
    for item in lista_produtos:
        for _ in range(int(item['qtd'])):
            # Gera código de barras
            code128 = barcode.get('code128', str(item['codigo']), writer=ImageWriter())
            code128.save('temp_barcode', options={"write_text": False, "module_width": 0.2, "module_height": 5.0})
            
            # Desenha a borda da etiqueta
            c.rect(2*mm, 2*mm, 66*mm, 46*mm)
            # Linha horizontal divisória
            c.line(2*mm, 25*mm, 68*mm, 25*mm)
            
            # Adiciona a imagem 'download.png' (Posicionada na parte superior esquerda)
            if os.path.exists("download.png"):
                c.drawImage("download.png", 5*mm, 30*mm, width=15*mm, height=15*mm, preserveAspectRatio=True)
            
            # Nome do Produto (Parte superior)
            estilo = ParagraphStyle('nome', fontSize=10, leading=12, alignment=1) # alignment=1 centraliza
            p_nome = Paragraph(f"<b>{item['nome']}</b>", estilo)
            p_nome.wrapOn(c, 45*mm, 20*mm)
            p_nome.drawOn(c, 20*mm, 32*mm)
            
            # Referência e Frase (Parte inferior)
            estilo_inf = ParagraphStyle('inf', fontSize=9, leading=10)
            p_info = Paragraph(f"REF: <b>{item['codigo']}</b><br/>FABRICADO NO BRASIL", estilo_inf)
            p_info.wrapOn(c, 60*mm, 20*mm)
            p_info.drawOn(c, 5*mm, 15*mm)
            
            # Código de Barras (Parte inferior)
            c.drawImage('temp_barcode.png', 10*mm, 3*mm, width=50*mm, height=10*mm)
            
            c.showPage()
            
    c.save()
    return buffer.getvalue()

st.title("🏷️ Gerador de Etiquetas")
aba1, aba2 = st.tabs(["📄 Ler XML NFe", "📦 Consulta Manual"])

with aba1:
    uploaded_file = st.file_uploader("Upload XML", type="xml")
    if uploaded_file:
        try:
            root = ET.parse(uploaded_file).getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            itens = []
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                itens.append({'nome': prod.find('nfe:xProd', ns).text, 'codigo': prod.find('nfe:cProd', ns).text, 'qtd': 1})
            st.table(pd.DataFrame(itens))
            if st.button("Gerar Etiquetas do XML"):
                pdf = gerar_pdf_etiquetas_multiplas(itens)
                st.download_button("Baixar PDF", data=pdf, file_name="etiquetas_xml.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Erro ao processar XML: {e}")

with aba2:
    df = carregar_dados()
    
    # Filtros e Botão de Ação no Topo
    c_f1, c_f2, c_f3 = st.columns(3)
    with c_f1: filtro_fam = st.multiselect("Família:", df['Família de Produto'].unique())
    with c_f2: filtro_marca = st.multiselect("Marca:", df['Marca'].unique() if 'Marca' in df.columns else [])
    with c_f3: filtro_modelo = st.multiselect("Modelo:", df['Modelo'].unique() if 'Modelo' in df.columns else [])
    
    so_estoque = st.checkbox("Apenas estoque > 0", value=True)
    
    # Aplicação de filtros
    df_f = df.copy()
    if filtro_fam: df_f = df_f[df_f['Família de Produto'].isin(filtro_fam)]
    if filtro_marca and 'Marca' in df.columns: df_f = df_f[df_f['Marca'].isin(filtro_marca)]
    if filtro_modelo and 'Modelo' in df.columns: df_f = df_f[df_f['Modelo'].isin(filtro_modelo)]
    if so_estoque: df_f = df_f[df_f['Estoque Físico'] > 0]
    
    # Lógica de seleção em massa
    c_btn1, c_btn2 = st.columns([1, 4])
    with c_btn1:
        if st.button("Selecionar Todos"):
            for idx in df_f.index:
                st.session_state[f"check_{idx}"] = True
            # O Streamlit automaticamente rerun após o clique do botão,
            # então não é necessário chamar `experimental_rerun()`.

    # Botão de Gerar PDF
    if st.button("Preparar PDF"):
        lista_final = []
        for idx, row in df_f.iterrows():
            if st.session_state.get(f"check_{idx}", False):
                nome = row.get('Descrição') if 'Descrição' in row else row.get('nome', '')
                codigo = str(row.get('Código') if 'Código' in row else row.get('codigo', ''))
                qtd = st.session_state.get(f"q_{idx}", 1)
                lista_final.append({'nome': nome, 'codigo': codigo, 'qtd': qtd})

        if lista_final:
            st.session_state.pdf_data = gerar_pdf_etiquetas_multiplas(lista_final)
        else:
            st.warning("Selecione itens na lista abaixo.")

    # O botão de download aparece APENAS se o PDF foi gerado
    if 'pdf_data' in st.session_state:
        st.download_button(
            label="✅ Clique aqui para baixar o PDF",
            data=st.session_state.pdf_data,
            file_name="etiquetas.pdf",
            mime="application/pdf"
        )
    # ... (filtros e botão de selecionar todos no topo)

    st.write("---")
    
    # Adicionamos um contador para garantir que o loop está percorrendo o DataFrame
    if len(df_f) == 0:
        st.warning("Nenhum produto encontrado com os filtros atuais.")
    else:
        for index, p in df_f.iterrows():
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.write(f"**{p.get('Descrição', p.get('nome', ''))}**")
            # valor padrão para quantidade (garantir inteiro >=1)
            try:
                default_q = int(float(str(p.get('Estoque Físico', p.get('quantidade', 0))).replace(',', '.')))
            except Exception:
                default_q = 1
            if default_q < 1:
                default_q = 1
            c2.number_input("Qtd", value=default_q, key=f"q_{index}")
            c3.checkbox("Selecionar", key=f"check_{index}")