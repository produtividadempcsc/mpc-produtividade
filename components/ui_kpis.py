import streamlit as st

def render_gabinete_kpis(total_com_servidores: int, total_para_revisao: int, total_com_procurador: int, total_atrasados_mpc: int):
    """Renderiza os cartões de Indicadores Chave de Desempenho (KPIs) do gabinete."""
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_com_servidores}</div>
            <div class="kpi-label">Processos com Servidores</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #ffc107;">{total_para_revisao}</div>
            <div class="kpi-label">Processos para Revisão</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #17a2b8;">{total_com_procurador}</div>
            <div class="kpi-label">Processos com o Procurador</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: {'#DC3545' if total_atrasados_mpc > 0 else '#28A745'};">{total_atrasados_mpc}</div>
            <div class="kpi-label">Atrasados MPC</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Alerta para processos com prazo MPC vencido
    if total_atrasados_mpc > 0:
        st.error(f"⚠️ **ATENÇÃO:** {total_atrasados_mpc} processo(s) com prazo MPC vencido!")

def render_servidor_kpis(total_ativos: int, no_prazo: int, atrasados: int):
    """Renderiza os KPIs para a visão do servidor."""
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_ativos}</div>
            <div class="kpi-label">Processos Ativos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #28a745;">{no_prazo}</div>
            <div class="kpi-label">No Prazo</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #dc3545;">{atrasados}</div>
            <div class="kpi-label">Atrasados</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
