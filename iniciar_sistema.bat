@echo off
:: Define o título da janela principal para fácil identificação
TITLE Lançador do Sistema MPC/SC

:: Muda o diretório para a pasta onde o script está localizado
:: Isso garante que os comandos python/streamlit encontrem os arquivos certos
cd /d "%~dp0"

echo Iniciando os serviços do sistema MPC/SC...



:: Inicia a aplicação Streamlit em uma nova janela de terminal
start "App Streamlit MPC/SC" streamlit run app.py

echo Scripts iniciados. Esta janela se fechará em 5 segundos.
timeout /t 5