import streamlit as st
import os

def load_css(file_path="styles/main.css"):
    """
    Carrega o arquivo CSS centralizado e o injeta na página Streamlit.
    """
    try:
        # Tenta encontrar o arquivo CSS. 
        # Assume que o CWD é a raiz do projeto (onde app.py está).
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                css_content = f.read()
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        else:
            # Fallback ou log de aviso (silencioso por enquanto)
            print(f"Aviso: Arquivo CSS não encontrado em {file_path}")
    except Exception as e:
        print(f"Erro ao carregar CSS: {e}")

def load_page_specific_css(css_content):
    """
    Permite injetar CSS específico de uma página, se necessário (ex: animações únicas).
    """
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
