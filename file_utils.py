import os
import io
import zipfile
import fitz  # PyMuPDF
from PIL import Image
import docx
from fpdf import FPDF as FPDF_original
from fpdf.errors import FPDFException
import streamlit as st
from com_utils import convert_docx_to_pdf_threaded

# --- FUNÇÕES DE EXTRAÇÃO DE TEXTO (Usadas pela IA) ---

class FPDF(FPDF_original):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_dejavu = False
        try:
            self.add_font('DejaVu', '', 'assets/fonts/DejaVuSans.ttf', uni=True)
            self.has_dejavu = True
        except (FPDFException, FileNotFoundError, RuntimeError):
            # print("DejaVu font not found, falling back to Arial.")
            pass

    def set_font(self, family, style='', size=0):
        if family.lower() == 'dejavu' and not self.has_dejavu:
            super().set_font('Arial', style, size)
        else:
            super().set_font(family, style, size)

def extract_text_from_file(uploaded_file):
    """Extrai texto de arquivos PDF, DOCX ou TXT para análise da IA."""
    file_bytes = uploaded_file.getvalue()
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    try:
        if file_extension == ".pdf":
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in pdf_doc:
                text += page.get_text()
            return text
        elif file_extension == ".docx":
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        elif file_extension == ".txt":
            return file_bytes.decode('utf-8', 'replace')
        else:
            return f"Tipo de arquivo '{file_extension}' não suportado para extração de texto."
    except Exception as e:
        return f"Erro ao extrair texto do arquivo {uploaded_file.name}: {e}"

def process_uploaded_files(uploaded_files):
    """Processa lista de uploads e retorna dicionário com conteúdo."""
    processed_files = []
    for uploaded_file in uploaded_files:
        text_content = extract_text_from_file(uploaded_file)
        processed_files.append({'name': uploaded_file.name, 'content': text_content})
    return processed_files

# --- FUNÇÕES DE CONVERSÃO/MATERIALIZAÇÃO (Usadas apenas se houver necessidade de download) ---
# Mantidas pois AI_Central pode usar para gerar downloads de logs ou conversões no futuro
# Se não estiver sendo usado, poderíamos remover, mas 'materialize_attachments' parece ser usada em algum lugar?
# Verificação rápida: AI_Central usa process_uploaded_files. materialize_attachments não foi visto no grep anterior.
# Vou manter por segurança pois é utilitário puro, mas removi toda a parte de encryption/disk storage.

def materialize_attachments_memory(files_data) -> bytes:
    """
    Converte lista de conteudos (memoria) em PDF único.
    Diferente da versão anterior que lia do disco criptografado.
    """
    final_pdf = fitz.open()

    for file_info in files_data:
        try:
            # Assumindo que file_info tem 'bytes' e 'name'
            # Se vier do process_uploaded_files, tem 'content' (texto).
            # Esta função precisaria ser adaptada se fosse usada.
            pass
        except:
             pass
    return None

# Funções de criptografia REMOVIDAS pois o sistema não deve armazenar arquivos localmente.
