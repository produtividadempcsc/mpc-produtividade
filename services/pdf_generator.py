import pandas as pd
from datetime import datetime
from utils.timezone import now_brazil
from fpdf import FPDF

# ============================================================
# Constantes de Formatação e Helpers
# ============================================================
MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# Cores institucionais MPC/SC
_COR_AZUL  = (0, 51, 102)    # azul marinho
_COR_BRANCO = (255, 255, 255)
_COR_CINZA  = (245, 245, 245)
_COR_TEXTO  = (33, 33, 33)
_COR_BORDA  = (200, 200, 200)

def sanitize_text(text):
    if text is None: return ""
    text = str(text)
    replacements = {
        '\u2013': '-', # en dash
        '\u2014': '-', # em dash
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u2026': '...',
        '\u00a0': ' ', # non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', 'replace').decode('latin-1')

# ============================================================
# PDF Básico de Listagem (Dashboard)
# ============================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        try:
            self.image('logo_mpcsc.jpg', 10, 8, 33)
        except Exception:
            self.cell(0, 10, 'MPC/SC', 0, 0, 'L')
        self.cell(0, 10, sanitize_text('Relatório de Produtividade'), 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def gerar_relatorio_dashboard(df_processos: pd.DataFrame):
    pdf = PDF(orientation='L')
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, sanitize_text('Lista de Processos'), 0, 1, 'L')

    if df_processos.empty:
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, 'Nenhum processo encontrado para os filtros selecionados.', 0, 1)
        return bytes(pdf.output(dest='S'))

    pdf.set_font('Arial', 'B', 8)
    line_height = pdf.font_size * 2.5
    col_widths = {
        'Nº Processo': 25,
        'Servidor': 45,
        'Produto': 65,
        'Status Geral': 25,
        'Data Final': 25
    }
    headers = list(col_widths.keys())

    for i, header in enumerate(headers):
        pdf.cell(col_widths[header], line_height, sanitize_text(header), 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    for index, row in df_processos.iterrows():
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        max_y = y_start
        pdf.set_xy(x_start, y_start)
        pdf.multi_cell(col_widths['Nº Processo'], line_height, sanitize_text(row.get('Nº Processo')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())
        
        pdf.set_xy(x_start + col_widths['Nº Processo'], y_start)
        pdf.multi_cell(col_widths['Servidor'], line_height, sanitize_text(row.get('Servidor')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())

        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'], y_start)
        pdf.multi_cell(col_widths['Produto'], line_height, sanitize_text(row.get('Produto')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())

        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'] + col_widths['Produto'], y_start)
        pdf.multi_cell(col_widths['Status Geral'], line_height, sanitize_text(row.get('Status Geral')), border=1, align='C')
        max_y = max(max_y, pdf.get_y())
        
        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'] + col_widths['Produto'] + col_widths['Status Geral'], y_start)
        pdf.multi_cell(col_widths['Data Final'], line_height, sanitize_text(row.get('Data Final')), border=1, align='C')
        max_y = max(max_y, pdf.get_y())

        pdf.set_y(max_y)
        
    return bytes(pdf.output(dest='S'))

def gerar_relatorio_detalhado(df_processos: pd.DataFrame):
    pdf = PDF(orientation='L')
    pdf.add_page()

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, sanitize_text('Relatório Detalhado de Processos'), 0, 1, 'C')
    pdf.ln()

    if df_processos.empty:
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, 'Nenhum processo encontrado para os filtros selecionados.', 0, 1)
        return bytes(pdf.output(dest='S'))

    pdf.set_font('Arial', 'B', 8)
    
    headers = [
        "Status", "Nº Processo", "Servidor",
        "Data Atribuição Servidor", "Prazo Servidor", "Data Conclusão Servidor",
        "Data Atribuição Chefe", "Prazo Chefe", "Data Conclusão"
    ]
    
    col_widths = {
        "Status": 20, "Nº Processo": 45, "Servidor": 40,
        "Data Atribuição Servidor": 38, "Prazo Servidor": 20, "Data Conclusão Servidor": 38,
        "Data Atribuição Chefe": 35, "Prazo Chefe": 20, "Data Conclusão": 25
    }

    for header in headers:
        pdf.cell(col_widths[header], 10, sanitize_text(header), 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    
    for _, row in df_processos.iterrows():
        status = row.get('status_servidor', 'N/A')

        if status == "Atrasado": pdf.set_fill_color(255, 102, 102)
        elif status == "No Prazo": pdf.set_fill_color(102, 255, 102)
        elif status == "Concluído": pdf.set_fill_color(173, 216, 230)
        else: pdf.set_fill_color(255, 255, 255)

        pdf.cell(col_widths["Status"], 10, sanitize_text(status), 1, 0, 'C', fill=True)
        pdf.cell(col_widths["Nº Processo"], 10, sanitize_text(row.get('processo_numero')), 1)
        pdf.cell(col_widths["Servidor"], 10, sanitize_text(row.get('servidor_responsavel_nome')), 1)
        pdf.cell(col_widths["Data Atribuição Servidor"], 10, sanitize_text(str(row.get('data_atribuicao_servidor', ''))), 1)
        pdf.cell(col_widths["Prazo Servidor"], 10, sanitize_text(str(row.get('prazo_servidor_aplicado', ''))), 1)
        pdf.cell(col_widths["Data Conclusão Servidor"], 10, sanitize_text(str(row.get('data_conclusao_servidor', ''))), 1)
        pdf.cell(col_widths["Data Atribuição Chefe"], 10, sanitize_text(str(row.get('data_atribuicao_chefe', ''))), 1)
        pdf.cell(col_widths["Prazo Chefe"], 10, sanitize_text(str(row.get('prazo_chefe_aplicado', ''))), 1)
        pdf.cell(col_widths["Data Conclusão"], 10, sanitize_text(str(row.get('data_conclusao_chefe', ''))), 1)
        pdf.ln()
        
    return bytes(pdf.output(dest='S'))

# ============================================================
# PDF Avançado (Métricas Mensais)
# ============================================================
class PDFRelatorio(FPDF):
    """PDF personalizado para o Relatório Mensal de Produtividade."""

    def __init__(self, titulo_cabecalho, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titulo_cabecalho = titulo_cabecalho
        self.set_margins(left=18, top=18, right=18)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        try:
            self.image('logo_mpcsc.jpg', x=18, y=10, h=18)
        except Exception:
            pass

        self.set_xy(50, 10)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*_COR_AZUL)
        self.cell(0, 6, sanitize_text('Ministério Público de Santa Catarina'), ln=True, align='R')

        self.set_x(50)
        self.set_font('Arial', '', 9)
        self.set_text_color(*_COR_TEXTO)
        self.cell(0, 5, sanitize_text(self.titulo_cabecalho), ln=True, align='R')

        self.set_draw_color(*_COR_AZUL)
        self.set_line_width(0.6)
        self.line(18, 32, self.w - 18, 32)
        self.ln(10)
        self.set_line_width(0.2)
        self.set_draw_color(*_COR_BORDA)

    def footer(self):
        self.set_y(-13)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, sanitize_text(f'Página {self.page_no()} / {{nb}}'), align='C')

    def secao_metrica(self, numero, titulo, dados, label_col1="Procurador(a)"):
        self.set_fill_color(*_COR_AZUL)
        self.set_text_color(*_COR_BRANCO)
        self.set_font('Arial', 'B', 9)
        self.cell(0, 7, sanitize_text(f'  {numero}. {titulo}'), fill=True, ln=True)
        self.ln(1)

        if not dados:
            self.set_font('Arial', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, sanitize_text('  Nenhum dado disponível para o período.'), ln=True)
            self.ln(3)
            return

        self.set_text_color(*_COR_BRANCO)
        self.set_fill_color(40, 80, 140)
        self.set_font('Arial', 'B', 8)
        col_w_proc  = self.w - self.l_margin - self.r_margin - 35
        col_w_valor = 35
        self.cell(col_w_proc,  6, sanitize_text(label_col1), border=0, fill=True, align='L')
        self.cell(col_w_valor, 6, sanitize_text('Valor'),         border=0, fill=True, align='C', ln=True)

        self.set_font('Arial', '', 8)
        for i, (chave_dado, valor) in enumerate(dados.items()):
            if i % 2 == 0:
                self.set_fill_color(*_COR_BRANCO)
            else:
                self.set_fill_color(*_COR_CINZA)
            self.set_text_color(*_COR_TEXTO)

            if isinstance(valor, float):
                valor_fmt = f'{valor:.2f}'
            else:
                valor_fmt = str(valor)

            texto_col1 = sanitize_text(f'  {chave_dado}')
            
            width_txt = self.get_string_width(texto_col1)
            linhas_estimadas = max(1, int(width_txt / (col_w_proc - 4)) + 1)
            h_estimada = linhas_estimadas * 6
            
            if self.get_y() + h_estimada > self.h - self.b_margin:
                self.add_page()

            x_start = self.get_x()
            y_start = self.get_y()

            self.multi_cell(col_w_proc, 6, texto_col1, border=0, fill=True, align='L')
            y_end = self.get_y()
            h_real = y_end - y_start

            self.set_xy(x_start + col_w_proc, y_start)
            self.cell(col_w_valor, h_real, sanitize_text(valor_fmt), border=0, fill=True, align='C', ln=True)
            
            self.set_y(y_end)

        self.set_draw_color(*_COR_BORDA)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

def gerar_relatorio_pdf(metricas: dict, mes: int, ano: int) -> bytes:
    mes_nome       = MESES_NOME.get(mes, str(mes))
    periodo        = f'{mes_nome}/{ano}'
    data_geracao   = now_brazil().strftime('%d/%m/%Y %H:%M')
    titulo_top     = f'Relat\u00f3rio Mensal de Produtividade - {periodo}'

    pdf = PDFRelatorio(titulo_cabecalho=titulo_top, orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*_COR_AZUL)
    pdf.cell(0, 8, sanitize_text('RELATÓRIO MENSAL DE PRODUTIVIDADE'), ln=True, align='C')
    pdf.ln(1)

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*_COR_TEXTO)
    infos = [
        ('Período de Referência:', periodo),
        ('Data do Relatório:',     data_geracao),
        ('Origem:',                'Produzido automaticamente pelo Sistema de Produtividade MPC/SC'),
    ]
    for label, valor in infos:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(52, 5, sanitize_text(label))
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, sanitize_text(valor), ln=True)

    pdf.ln(3)
    pdf.set_draw_color(*_COR_AZUL)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*_COR_BORDA)

    titulos_curtos = {
        "1)": "Número de processos concluídos pelos pareceristas no mês",
        "2)": "Média de dias para concluir o processo (por procurador)",
        "3)": "Percentual de processos concluídos no prazo (por procurador)",
        "4)": "Acervo não concluído ao encerrar o mês (por procurador)",
        "5)": "Número de processos revisados no mês (por procurador)",
        "6)": "Média de dias para o Chefe finalizar a revisão (por procurador)",
        "7)": "Percentual de revisões pelo Chefe concluídas no prazo",
        "8)": "Acervo não revisado pelo Chefe ao encerrar o mês",
        "9)": "Tempo médio de produção de produtos (por Procuradoria)",
        "10)": "Tempo médio de produção (por tipo de processo/procedimento)",
    }

    def parse_metric_idx(k):
        try:
            return int(k.split(')')[0].strip())
        except ValueError:
            return 999

    for numero, (chave, dados) in enumerate(sorted(metricas.items(), key=lambda x: parse_metric_idx(x[0])), start=1):
        prefixo = chave.split(')')[0].strip() + ')'
        titulo  = titulos_curtos.get(prefixo, chave.split(')')[0].strip() if ')' in chave else chave[:80])
        
        label_col1 = "Tipo de Processo/Procedimento" if prefixo == "10)" else "Procurador(a)"
        pdf.secao_metrica(numero, titulo, dados if isinstance(dados, dict) else {}, label_col1=label_col1)

    output = pdf.output(dest='S')
    return output.encode('latin-1') if isinstance(output, str) else bytes(output)

def gerar_relatorio_periodo_pdf(metricas: dict, ano: int, nome_periodo: str) -> bytes:
    periodo = f'{nome_periodo}/{ano}'
    data_geracao = now_brazil().strftime('%d/%m/%Y %H:%M')
    titulo_top = f'Relat\u00f3rio de Produtividade - {periodo}'

    pdf = PDFRelatorio(titulo_cabecalho=titulo_top, orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*_COR_AZUL)
    pdf.cell(0, 8, sanitize_text(f'RELAT\u00d3RIO DE PRODUTIVIDADE - {nome_periodo.upper()}'), ln=True, align='C')
    pdf.ln(1)

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*_COR_TEXTO)
    infos = [
        ('Período de Referência:', periodo),
        ('Data do Relatório:', data_geracao),
        ('Origem:', 'Produzido automaticamente pelo Sistema de Produtividade MPC/SC'),
    ]
    for label, valor in infos:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(52, 5, sanitize_text(label))
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, sanitize_text(valor), ln=True)

    pdf.ln(3)
    pdf.set_draw_color(*_COR_AZUL)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*_COR_BORDA)

    titulos_curtos = {
        "1)": "Processos concluídos pelos pareceristas no período",
        "2)": "Média de dias para concluir o processo (por procurador)",
        "3)": "Percentual de processos concluídos no prazo (por procurador)",
        "4)": "Acervo não concluído ao encerrar o período (por procurador)",
        "5)": "Processos revisados no período (por procurador)",
        "6)": "Média de dias para o Chefe finalizar a revisão (por procurador)",
        "7)": "Percentual de revisões pelo Chefe concluídas no prazo",
        "8)": "Acervo não revisado pelo Chefe ao encerrar o período",
        "9)": "Tempo médio de produção de produtos (por Procuradoria)",
        "10)": "Tempo médio de produção (por tipo de processo/procedimento)",
    }

    def parse_metric_idx(k):
        try:
            return int(k.split(')')[0].strip())
        except ValueError:
            return 999

    for numero, (chave, dados) in enumerate(sorted(metricas.items(), key=lambda x: parse_metric_idx(x[0])), start=1):
        prefixo = chave.split(')')[0].strip() + ')'
        titulo = titulos_curtos.get(prefixo, chave.split(')')[0].strip() if ')' in chave else chave[:80])
        
        label_col1 = "Tipo de Processo/Procedimento" if prefixo == "10)" else "Procurador(a)"
        pdf.secao_metrica(numero, titulo, dados if isinstance(dados, dict) else {}, label_col1=label_col1)

    output = pdf.output(dest='S')
    return output.encode('latin-1') if isinstance(output, str) else bytes(output)
