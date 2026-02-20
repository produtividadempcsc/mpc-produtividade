import streamlit as st
import sys
import os

# Adicionar diretório raiz ao path para importar módulos do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

import backup

st.set_page_config(page_title="Teste de Backup", page_icon="💾")

st.title("🛠️ Teste de Backup e Email")

st.markdown("""
Este script permite testar manualmente a execução do backup e o envio do email.
Certifique-se de que as credenciais de email estão configuradas corretamente no `.streamlit/secrets.toml`.
""")

if st.button("🚀 Executar Backup Manual e Enviar Email"):
    with st.spinner("⏳ Gerando backup e enviando email... Por favor, aguarde."):
        # Tenta executar o backup manual
        try:
            sucesso, mensagem = backup.executar_backup_manual_e_enviar_email()
            
            if sucesso:
                st.success(f"✅ {mensagem}")
                st.balloons()
            else:
                st.error(f"❌ {mensagem}")
        except Exception as e:
            st.error(f"❌ Erro crítico ao executar o teste: {e}")
            st.exception(e)
