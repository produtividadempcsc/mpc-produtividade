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

# Re-exportar todas as funções de utils.ui para manter compatibilidade
# com pages e components que usam `import ui_utils` e chamam
# ui_utils.display_icon_legend(), ui_utils.get_status_emoji(), etc.
from utils.ui import (
    load_logo,
    get_status_color,
    get_status_emoji,
    display_icon_legend,
    display_file,
    display_suspensos_expander,
    display_process_history,
    set_success_feedback,
    show_feedback_banner,
)
