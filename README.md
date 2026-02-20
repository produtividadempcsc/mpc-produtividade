# Sistema de Gestão de Produtividade - V11
### Ministério Público de Contas do Estado de Santa Catarina (MPC/SC)

Aplicação web desenvolvida em **Streamlit** para gerenciamento de produtividade, controle de prazos processuais e automação de relatórios do MPC/SC.

---

## 🚀 Funcionalidades Principais

### 📋 Gestão de Processos e Prazos
- Fluxo completo: **Servidor → Chefe de Gabinete → Procurador**
- Cálculo automático de prazos (dias úteis e corridos), considerando feriados, afastamentos e suspensões
- Classificação automática de status: "No Prazo", "Atrasado", "Concluído", "Devolvido", etc.
- Suporte a devoluções entre etapas (Procurador → Chefe, Chefe → Servidor)
- Processos que pulam etapas: "Não se aplica prazo ao servidor", "Ignorar revisão do chefe", "Ignorar análise do procurador"
- Gestão de substituições temporárias entre servidores
- Prazo MPC (prazo por setor)

### 🔔 Automação e Notificações (Worker Integrado)
- **Worker de background** com APScheduler — executa junto com a aplicação
- **Alertas de prazo**: e-mails automáticos para processos próximos do vencimento ou atrasados
- **Relatórios mensais**: geração e envio automático de relatórios de produtividade em PDF/Excel
- **Backup diário**: rotina automática de backup dos dados críticos com envio por e-mail

### 🤖 Inteligência Artificial
- **AI Central**: assistente integrado com Google Gemini para análise de documentos e geração de pareceres
- Banco de prompts reutilizáveis
- Upload e análise de PDFs

### 📊 Relatórios e Análises
- **Relatório mensal de produtividade**: 9 métricas por Procurador (quantidade, tempo médio, % no prazo, acervo pendente) — exportável em PDF e Excel
- **Relatório da Corregedoria**: métricas consolidadas para órgão de controle
- **Página analítica**: gráficos interativos com Plotly
- **MPC em Números**: dashboard gerencial consolidado do MPC
- **Gabinete em Números**: dashboard BI por gabinete (histório de acervo, distribuição, evolução)
- **Meus Dados**: dashboard BI individual para servidores

### 📱 Progressive Web App (PWA)
- Suporte a instalação como aplicativo nativo (manifest.json + service-worker.js)
- Página de fallback offline
- Cache inteligente de recursos estáticos

### 🔐 Segurança e Acesso
- Autenticação com senha criptografada (bcrypt)
- Controle de acesso por perfil (RBAC):
  - 🛡️ **Administrador** — gestão total do sistema
  - ⚖️ **Procurador** — visão gerencial e finalização de processos
  - 👔 **Chefe de Gabinete** — supervisão e revisão de processos
  - 👤 **Servidor** — gestão de processos atribuídos

---

## 🛠️ Stack Tecnológico

| Componente | Tecnologia |
|---|---|
| **Aplicação** | [Streamlit](https://streamlit.io/) |
| **Banco de dados** | [Supabase](https://supabase.com/) (PostgreSQL) |
| **Linguagem** | Python 3.9+ |
| **IA** | Google Gemini (google-genai) |
| **Gráficos** | Plotly |
| **Tarefas de background** | APScheduler |
| **Segurança** | bcrypt, cryptography |
| **Relatórios** | fpdf2 (PDF), openpyxl (Excel), python-docx (Word) |
| **Processamento de dados** | pandas, numpy |
| **PWA** | Service Worker, Web App Manifest |

---

## ⚙️ Configuração e Instalação

### Pré-requisitos
- Python 3.9 ou superior
- Conta no Supabase configurada com as tabelas necessárias

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

Crie um arquivo `.streamlit/secrets.toml` com as credenciais:

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

```
mpcsc_produtividade - V11/
│
├── app.py                  # Ponto de entrada da aplicação + injeção PWA
├── auth.py                 # Autenticação e gestão de sessão
├── sidebar.py              # Menu lateral com navegação por perfil
├── relatorios.py           # Métricas mensais de produtividade (9 métricas)
├── reports_corregedoria.py # Relatórios para a Corregedoria
├── backup.py               # Rotinas de backup e restauração
├── supabase_client.py      # Cliente de conexão com Supabase
├── db_compat.py            # Camada de compatibilidade com banco de dados
├── com_utils.py            # Utilitários de comentários
├── file_utils.py           # Utilitários de manipulação de arquivos
├── ui_utils.py             # Utilitários de interface
│
├── manifest.json           # PWA — Web App Manifest
├── service-worker.js       # PWA — Service Worker (cache e fallback offline)
├── logo_mpcsc.jpg          # Logo do MPC/SC (usada no PWA e relatórios)
│
├── pages/                  # Páginas do sistema (Streamlit Multipage)
│   ├── Meus_Processos.py           # Processos atribuídos ao servidor
│   ├── Processos_no_Gabinete.py    # Visão do chefe de gabinete
│   ├── Processos_para_Revisao.py   # Fila de revisão do chefe
│   ├── Processos_com_Procurador.py # Processos na etapa do procurador
│   ├── Processos_MPC.py            # Visão geral de processos MPC
│   ├── Pagina_Analitica.py         # Gráficos e análises
│   ├── Gabinete_em_Numeros.py      # Dashboard BI do gabinete
│   ├── MPC_em_Numeros.py           # Dashboard gerencial consolidado
│   ├── Meus_Dados.py               # Dashboard BI individual
│   ├── AI_Central.py               # Assistente de IA (Gemini)
│   ├── Administracao.py            # Painel administrativo
│   ├── Gerenciar_Usuarios.py       # CRUD de usuários
│   ├── Gerenciar_Substituicoes.py  # Substituições temporárias
│   ├── Gestao_Afastamentos.py      # Férias, licenças e atestados
│   ├── Comentarios_Processo.py     # Comentários em processos
│   ├── Meu_Perfil.py               # Perfil do usuário
│   └── Manual_do_Usuario.py        # Manual integrado
│
├── forms/                  # Formulários de entrada de dados
│   ├── processo.py                 # Formulário de processos
│   ├── actions.py                  # Ações sobre processos (concluir, devolver, etc.)
│   └── admin.py                    # Formulários administrativos
│
├── services/               # Serviços de negócio
│   └── prazo_service.py            # Cálculo de prazos e data-limite
│
├── repositories/           # Camada de acesso a dados
│   ├── afastamento_repository.py   # Consultas de afastamentos
│   └── calendar_repository.py      # Consultas de feriados
│
├── utils/                  # Utilitários compartilhados
│   ├── jobs.py                     # Tarefas de background (alertas, relatórios, backup)
│   ├── notifications.py            # Envio de e-mails
│   ├── ui.py                       # Componentes visuais reutilizáveis
│   ├── common.py                   # Funções utilitárias comuns
│   ├── analytics_utils.py          # Utilitários para gráficos e análises
│   └── timezone.py                 # Configuração de fuso horário
│
├── styles/                 # Folhas de estilo CSS
│   ├── main.css                    # Estilos gerais
│   ├── admin.css                   # Estilos de administração
│   ├── afastamentos.css            # Estilos de afastamentos
│   ├── ai_valor.css                # Estilos da AI Central
│   ├── chat.css                    # Estilos do chat
│   ├── prompt_bank.css             # Estilos do banco de prompts
│   └── timeline.css                # Estilos da timeline de processos
│
├── docs/                   # Documentação
│   └── explicacao_metricas_relatorio_mensal.md
│
├── scripts/                # Scripts utilitários
│   ├── backfill_data.py            # Preenchimento retroativo de dados
│   └── test_backup_email.py        # Teste de envio de e-mail de backup
│
├── tests/                  # Testes automatizados
│   ├── test_analytics.py           # Testes de análises e gráficos
│   ├── test_calendar_leaves.py     # Testes de feriados e afastamentos
│   ├── test_data_generator.py      # Gerador de dados de teste
│   ├── test_integration_processos.py # Testes de integração de processos
│   ├── test_new_formulas.py        # Testes de novas fórmulas de cálculo
│   ├── test_permissions_substitutions.py # Testes de permissões e substituições
│   ├── test_prazos.py              # Testes de cálculo de prazos
│   ├── test_prazos_notificacoes.py # Testes de notificações de prazos
│   └── diagnose_users.py           # Diagnóstico de dados de usuários
│
├── manual_administrador.txt    # Manual do administrador
├── manual_chefe_gabinete.txt   # Manual do chefe de gabinete
├── manual_procurador.txt       # Manual do procurador
├── manual_servidor.txt         # Manual do servidor
│
├── requirements.txt        # Dependências do projeto
└── iniciar_sistema.bat     # Script de inicialização (Windows)
```

---

## 🧪 Testes

Execute os testes automatizados com:

```bash
python -m pytest tests/ -v
```

Os testes cobrem:
- Cálculo de prazos e status de processos
- Permissões e substituições de usuários
- Feriados e afastamentos
- Integração de fluxo de processos
- Notificações de prazos
- Análises e gráficos

---

## 📝 Licença

Desenvolvido para uso interno do Ministério Público de Contas de Santa Catarina.
Todos os direitos reservados.
