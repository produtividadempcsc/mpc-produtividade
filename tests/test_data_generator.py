"""
Gerador de Dados de Teste para o Sistema de Processos MPCSC
============================================================
Este módulo fornece funções para gerar dados realísticos de teste
para os scripts de automação.
"""

import random
import string
from datetime import date, timedelta
from typing import List, Dict, Optional

# Prefixo para identificar processos de teste
TEST_PREFIX = "TEST"

# Contador global para números sequenciais
_process_counter = 0


def generate_process_number() -> str:
    """
    Gera um número de processo de teste único no formato TEST-YYYYMMDD-XXXX.
    """
    global _process_counter
    _process_counter += 1
    today = date.today().strftime("%Y%m%d")
    return f"{TEST_PREFIX}-{today}-{_process_counter:04d}"


def generate_random_process_number() -> str:
    """
    Gera um número de processo aleatório no formato TEST-XXXXX-XXXX.XXXX.XX.XXXX.X.XX.XXXX.
    Simula o formato real de processos judiciais.
    """
    global _process_counter
    _process_counter += 1
    
    # Formato simplificado para testes
    seq = random.randint(10000, 99999)
    ano = random.randint(2020, 2026)
    unidade = random.randint(1, 99)
    
    return f"{TEST_PREFIX}-{seq:05d}-{ano}.{unidade:02d}.{_process_counter:04d}"


def reset_counter():
    """Reseta o contador de processos."""
    global _process_counter
    _process_counter = 0


def get_random_priority() -> str:
    """Retorna uma prioridade aleatória com peso realístico."""
    priorities = ['Regular', 'Regular', 'Regular', 'Prioritário', 'Urgente']
    return random.choice(priorities)


def get_random_observation() -> Optional[str]:
    """Retorna uma observação aleatória ou None."""
    observations = [
        None,
        None,
        "Processo requer atenção especial.",
        "Verificar documentação anexa.",
        "Prazo curto - priorizar análise.",
        "Processo de teste para validação do sistema.",
        "Aguardando documentos complementares.",
        "Reanálise solicitada.",
    ]
    return random.choice(observations)


def get_random_date_in_range(start_days_ago: int = 30, end_days_ago: int = 0) -> date:
    """
    Retorna uma data aleatória entre start_days_ago e end_days_ago no passado.
    """
    days_ago = random.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=days_ago)


def generate_test_process_data(
    servidor_id: int,
    chefe_id: int,
    procurador_id: int,
    tipo_produto_id: int,
    prazo_servidor: int = 5,
    prazo_chefe: int = 3,
    **kwargs
) -> Dict:
    """
    Gera um dicionário com dados de processo pronto para inserção.
    
    Args:
        servidor_id: ID do servidor responsável
        chefe_id: ID do chefe de gabinete
        procurador_id: ID do procurador
        tipo_produto_id: ID do tipo de produto
        prazo_servidor: Prazo em dias para o servidor
        prazo_chefe: Prazo em dias para o chefe
        **kwargs: Campos adicionais para sobrescrever
        
    Returns:
        Dicionário com dados do processo
    """
    data_atribuicao = kwargs.pop('data_atribuicao', date.today())
    
    processo_data = {
        "processo_numero": generate_process_number(),
        "id_procurador": procurador_id,
        "id_chefe_gabinete": chefe_id,
        "id_servidor_responsavel": servidor_id,
        "id_tipo_produto": tipo_produto_id,
        "data_atribuicao_servidor": data_atribuicao.isoformat(),
        "status_servidor": "No Prazo",
        "status_chefe": "Aguardando Análise",
        "prazo_servidor_aplicado": prazo_servidor,
        "prazo_chefe_aplicado": prazo_chefe,
        "nao_se_aplica_prazo_servidor": False,
        "ignorar_revisao_chefe": False,
        "ignorar_analise_procurador": False,
        "prioridade": get_random_priority(),
        "observacao_chefe": get_random_observation(),
    }
    
    # Sobrescrever com kwargs
    processo_data.update(kwargs)
    
    return processo_data


def generate_batch_process_data(
    servidores: List[Dict],
    chefes: List[Dict],
    procuradores: List[Dict],
    tipos_produto: List[Dict],
    count: int = 10
) -> List[Dict]:
    """
    Gera múltiplos processos de teste com distribuição aleatória entre usuários.
    
    Args:
        servidores: Lista de usuários servidores
        chefes: Lista de usuários chefes de gabinete
        procuradores: Lista de usuários procuradores
        tipos_produto: Lista de tipos de produto
        count: Quantidade de processos a gerar
        
    Returns:
        Lista de dicionários com dados de processos
    """
    if not servidores or not chefes or not procuradores or not tipos_produto:
        raise ValueError("Todas as listas de usuários e tipos de produto devem ter pelo menos um item.")
    
    processes = []
    
    for i in range(count):
        servidor = random.choice(servidores)
        chefe = random.choice(chefes)
        procurador = random.choice(procuradores)
        produto = random.choice(tipos_produto)
        
        # Variar datas de atribuição para simular processos em diferentes estágios
        days_ago = random.randint(0, 20)
        data_atribuicao = date.today() - timedelta(days=days_ago)
        
        processo = generate_test_process_data(
            servidor_id=servidor['id'],
            chefe_id=chefe['id'],
            procurador_id=procurador['id'],
            tipo_produto_id=produto['id'],
            prazo_servidor=produto.get('prazo_servidor', 5),
            prazo_chefe=produto.get('prazo_chefe', 3),
            data_atribuicao=data_atribuicao
        )
        
        processes.append(processo)
    
    return processes


def is_test_process(processo_numero: str) -> bool:
    """Verifica se um processo é de teste baseado no prefixo."""
    return processo_numero.startswith(TEST_PREFIX)


# Cenários de teste pré-definidos
TEST_SCENARIOS = {
    "basic_flow": {
        "description": "Fluxo básico: Servidor conclui, Chefe aprova, Procurador finaliza",
        "steps": ["create", "servidor_conclude", "chefe_approve", "procurador_finalize"]
    },
    "chefe_return": {
        "description": "Chefe devolve processo ao servidor",
        "steps": ["create", "servidor_conclude", "chefe_return", "servidor_conclude", "chefe_approve"]
    },
    "skip_chefe": {
        "description": "Ignora revisão do chefe",
        "config": {"ignorar_revisao_chefe": True},
        "steps": ["create", "servidor_conclude", "procurador_finalize"]
    },
    "skip_procurador": {
        "description": "Ignora análise do procurador", 
        "config": {"ignorar_analise_procurador": True},
        "steps": ["create", "servidor_conclude", "chefe_approve"]
    },
    "full_skip": {
        "description": "Ignora tanto chefe quanto procurador",
        "config": {"ignorar_revisao_chefe": True, "ignorar_analise_procurador": True},
        "steps": ["create", "servidor_conclude"]
    },
    "urgent_priority": {
        "description": "Processo urgente",
        "config": {"prioridade": "Urgente"},
        "steps": ["create", "servidor_conclude", "chefe_approve"]
    }
}


if __name__ == "__main__":
    # Teste básico do gerador
    print("=== Teste do Gerador de Dados ===")
    
    # Simular usuários
    mock_servidores = [{"id": 1, "nome_completo": "Servidor Teste"}]
    mock_chefes = [{"id": 2, "nome_completo": "Chefe Teste"}]
    mock_procuradores = [{"id": 3, "nome_completo": "Procurador Teste"}]
    mock_produtos = [{"id": 1, "nome_produto": "Produto Teste", "prazo_servidor": 5, "prazo_chefe": 3}]
    
    print("\n1. Gerando número de processo:")
    print(f"   {generate_process_number()}")
    print(f"   {generate_process_number()}")
    
    print("\n2. Gerando processo completo:")
    processo = generate_test_process_data(
        servidor_id=1, chefe_id=2, procurador_id=3, tipo_produto_id=1
    )
    for key, value in processo.items():
        print(f"   {key}: {value}")
    
    print("\n3. Gerando batch de 3 processos:")
    reset_counter()
    batch = generate_batch_process_data(
        mock_servidores, mock_chefes, mock_procuradores, mock_produtos, count=3
    )
    for i, p in enumerate(batch):
        print(f"   [{i+1}] {p['processo_numero']} - {p['prioridade']}")
    
    print("\n=== Teste concluído ===")
