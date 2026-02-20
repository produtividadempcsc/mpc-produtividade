
import os
import sys
import unittest
from datetime import date, datetime, timedelta
import time
import uuid
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import QueryBuilder, insert, update_by_id, delete_by_id, select_all
from db_compat import get_user_by_id, update_process

# Importar as funcoes reais de analytics
from pages.analytics_utils import (
    prepare_master_dataframe, 
    calculate_metrics_servidor
)

class TestAnalytics(unittest.TestCase):
    
    def setUp(self):
        """Setup: Criar Servidor de teste + Massa de Dados"""
        self.created_data = {"users": [], "processes": []}
        
        # 1. Criar Servidor Fake
        servidor_data = {
            "nome_completo": f"Servidor Analytics {int(time.time())}",
            "login": f"serv.ana.{uuid.uuid4().hex[:8]}",
            "senha_hash": "hash_fake",
            "perfil": "Servidor",
            "email": f"serv.ana.{uuid.uuid4().hex[:8]}@test.com",
            "ativo": True
        }
        self.servidor = insert("usuarios", servidor_data)
        self.created_data["users"].append(self.servidor['id'])
        self.servidor_id = self.servidor['id']
        
        # 2. Criar Massa de Dados (Histórico)
        hoje = date.today()
        # Periodo que engloba hoje e mes passado para garantir dados
        self.inicio_periodo = hoje - timedelta(days=60)
        self.fim_periodo = hoje
        
        print(f"\n[SETUP] Gerando dados desde: {self.inicio_periodo}")
        
        # Criar 10 Processos Concluídos no Prazo
        for i in range(10):
            # Concluidos ha 10 dias
            ref_date = hoje - timedelta(days=10)
            self._create_processed_item("No Prazo", ref_date)
            
        # Criar 5 Processos Atrasados
        for i in range(5):
            ref_date = hoje - timedelta(days=10)
            self._create_processed_item("Atrasado", ref_date)
            
    def _create_processed_item(self, status, date_conclusao):
        # Para ser "No Prazo", data_conclusao <= data_atribuicao + prazo
        # Para ser "Atrasado", data_conclusao > data_atribuicao + prazo
        
        prazo_aplicado = 5
        if status == "No Prazo":
            data_atrib = date_conclusao - timedelta(days=2) # Concluiu em 2 dias (ok)
        else:
            data_atrib = date_conclusao - timedelta(days=10) # Concluiu em 10 dias (atrasado)
            
        p_data = {
            "processo_numero": f"ANA-{uuid.uuid4().hex[:6]}",
            "id_tipo_produto": 1,
            "id_servidor_responsavel": self.servidor_id,
            "data_atribuicao_servidor": data_atrib.isoformat(),
            "data_conclusao_servidor": date_conclusao.isoformat(),
            "status_servidor": "Concluído",
            "prazo_servidor_aplicado": prazo_aplicado,
            # Importante: para métricas, precisamos garantir dados validos
            "id_chefe_gabinete": None, 
            "prazo_total_dias_suspenso": 0
        }
        proc = insert("processos", p_data)
        if proc: self.created_data["processes"].append(proc['id'])

    def tearDown(self):
        """Limpeza"""
        print("\n[TEARDOWN] Limpando dados de analytics...")
        for pid in self.created_data["processes"]:
            delete_by_id("processos", pid)
        for uid in self.created_data["users"]:
            delete_by_id("usuarios", uid)

    def test_relatorio_produtividade(self):
        """
        Teste 1: Validar contagem usando engine real do analytics.
        """
        print("\n[TEST] Verificando RELATÓRIO DE PRODUTIVIDADE...")
        
        # 1. Buscar Dados usando QueryBuilder direto (simulando o fetch da pagina)
        processos_raw = QueryBuilder("processos") \
            .eq("id_servidor_responsavel", self.servidor_id) \
            .execute()
            
        # 2. Obter dicionarios auxiliares (mockados ou reais)
        # Como criamos o usuario, ele existe. Tipo produto assumimos ID 1 existe.
        users_raw = select_all("usuarios")
        users_dict = {u['id']: u for u in users_raw}
        
        types_raw = select_all("tipos_produto")
        types_dict = {t['id']: t for t in types_raw}
        
        # 3. Chamar Engine do Analytics
        df_master = prepare_master_dataframe(processos_raw, users_dict, types_dict)
        df_metrics = calculate_metrics_servidor(df_master)
        
        # 4. Validar Resultados
        if df_metrics.empty:
            self.fail("DataFrame de métricas retornou vazio!")
            
        # Filtrar apenas os que criamos (pelo ID do servidor ja filtramos na query, mas ok)
        total_items = len(df_metrics)
        self.assertEqual(total_items, 15, f"Esperado 15 processos processados, obteve {total_items}")
        
        # Contar No Prazo vs Atrasado
        no_prazo = df_metrics[df_metrics['no_prazo_servidor'] == True].shape[0]
        atrasado = df_metrics[df_metrics['no_prazo_servidor'] == False].shape[0]
        
        self.assertEqual(no_prazo, 10, f"No Prazo: Esperado 10, Obtido {no_prazo}")
        self.assertEqual(atrasado, 5, f"Atrasado: Esperado 5, Obtido {atrasado}")
        
        print(f"   -> Métricas validadas com sucesso: {no_prazo} No Prazo, {atrasado} Atrasados")

if __name__ == '__main__':
    unittest.main()
