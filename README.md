# Sistema de Gestão de Produtividade
### Ministério Público de Contas do Estado de Santa Catarina (MPC/SC)

Este sistema é uma aplicação web desenvolvida em **Streamlit** para o gerenciamento de produtividade, controle de prazos processuais e automação de relatórios do MPC/SC.

---

## 🚀 Funcionalidades Principais

### 🔹 Gestão de Prazos e Processos
- Monitoramento automático de prazos para servidores e chefia.
- Cálculo de dias úteis, considerando feriados e suspensões (integrado ao banco de dados).
- Classificação automática de status: "No Prazo", "Atrasado", "Aguardando Análise", etc.

### 🔹 Automação e Notificações (Worker Integrado)
- **Worker de Background**: Executa automaticamente junto com a aplicação.
- **Alertas de Prazo**: Envio automático de e-mails para processos próximos do vencimento ou atrasados.
- **Relatórios Mensais**: Geração e envio de relatórios de produtividade em Excel.

### 🔹 Segurança e Acesso
- **Autenticação Segura**: Login com senha criptografada (bcrypt).
- **Controle de Acesso (RBAC)**: Perfis de usuário com permissões específicas:
    - 🛡️ **Administrador**: Gestão total do sistema.
    - 👔 **Chefe de Gabinete**: Supervisão e revisão de processos.
    - 👤 **Servidor**: Gestão de processos atribuídos.
    - ⚖️ **Procurador**: Visão gerencial jurídica.

### 🔹 Infraestrutura e Dados
- **Banco de Dados**: Supabase (PostgreSQL) para armazenamento seguro e escalável.
- **Backup**: Rotina automática de backup dos dados críticos.

---

## 🛠️ Stack Tecnológico

- **Frontend/App**: [Streamlit](https://streamlit.io/)
- **Banco de Dados**: Supabase (PostgreSQL)
- **Linguagem**: Python 3.9+
- **Bibliotecas Chave**:
    - `pandas`: Processamento de dados e relatórios.
    - `APScheduler`: Gerenciamento de tarefas em background (Worker).
    - `supabase`: Cliente de conexão com o banco de dados.
    - `bcrypt`: Segurança de senhas.
    - `plotly`: Visualização de dados e gráficos.

---

## ⚙️ Configuração e Instalação

### Pré-requisitos
- Python 3.9 ou superior instalado.
- Conta no Supabase configurada com as tabelas necessárias.

### Instalação

1. Clone o repositório ou baixe os arquivos.
2. Crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### Configuração de Segredos
Crie um arquivo `.streamlit/secrets.toml` com as credenciais do Supabase e configurações de e-mail:

```toml
[general]
SYSTEM_EMAIL = "seu-email@exemplo.com"
SYSTEM_EMAIL_PASSWORD = "senha-de-app"

GEMINI_API_KEY = "sua-chave-gemini"

# Configuração Supabase
SUPABASE_URL = "https://sua-url.supabase.co"
SUPABASE_KEY = "sua-chave-anon-ou-service"
```

---

## ▶️ Como Executar

### Via Script (Windows)
Execute o arquivo `iniciar_sistema.bat`. Ele iniciará a aplicação automaticamente.

### Via Terminal
```bash
streamlit run app.py
```

O sistema estará acessível em: `http://localhost:8501`

---

## 📂 Estrutura do Projeto

- `app.py`: Ponto de entrada da aplicação.
- `auth.py`: Módulo de autenticação e gestão de sessão.
- `db_compat.py`: Camada de compatibilidade e acesso ao banco de dados.
- `supabase_client.py`: Cliente de conexão direta com Supabase.
- `pages/`: Páginas do sistema (Streamlit Multipage).
- `utils/`:
    - `jobs.py`: Lógica de negócios das tarefas de background.
    - `worker_manager.py`: Gerenciador do scheduler.
    - `notifications.py`: Envio de e-mails.
- `assets/`: Arquivos estáticos (imagens, CSS).

---

## 📝 Licença
Desenvolvido para uso interno do Ministério Público de Contas de Santa Catarina.
Todos os direitos reservados.

