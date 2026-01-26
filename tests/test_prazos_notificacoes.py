
import os
import sys
import unittest
from datetime import date, datetime, timedelta
import time

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import QueryBuilder, insert, update_by_id, delete_by_id
from db_compat import (
    get_user_by_id, 
    get_product_type_by_name,
    calculate_due_date,
    create_notification,
    get_user_notifications
)

class TestPrazosNotificacoes(unittest.TestCase):
    
    def setUp(self):
        """Configuração inicial dos testes."""
        self.created_processes = []
        self.created_notifications = []
        
        # Buscar IDs de teste
        try:
            self.servidor = QueryBuilder("usuarios").eq("perfil", "Servidor").first()
            self.chefe = QueryBuilder("usuarios").eq("perfil", "Chefe de Gabinete").first()
            
            if not self.servidor or not self.chefe:
                self.skipTest("Usuários de teste não encontrados (Servidor/Chefe)")
                
            self.servidor_id = self.servidor['id']
            self.chefe_id = self.chefe['id']
            
            # Tipos de produto para teste
            self.produto_dias_uteis = self._ensure_product_type("TEST - Prazo Uteis", "dias uteis")
            self.produto_dias_corridos = self._ensure_product_type("TEST - Prazo Corridos", "dias corridos")
            
        except Exception as e:
            self.fail(f"Erro no setup: {e}")

    def tearDown(self):
        """Limpeza de dados."""
        print("\n[TEARDOWN] Limpando dados de teste...")
        for pid in self.created_processes:
            delete_by_id("processos", pid)
        
        for nid in self.created_notifications:
            delete_by_id("notificacoes", nid)

    def _ensure_product_type(self, name, tipo_contagem):
        """Garante que o tipo de produto existe."""
        existing = QueryBuilder("tipos_produto").eq("nome_produto", name).first()
        if existing:
            return existing
        
        data = {
            "nome_produto": name,
            "prazo_servidor": 5,
            "prazo_chefe": 2,
            "tipo_contagem_prazo": tipo_contagem,
            "versao": 1,
            "data_criacao": datetime.now().isoformat(),
            "nome_id": 9999  # ID alto para teste
        }
        return insert("tipos_produto", data)

    def test_calculo_dias_uteis(self):
        """
        Teste 1: Valida se o cálculo de dias úteis está correto (excluindo FDS).
        """
        print("\n[TEST] Verificando cálculo de DIAS ÚTEIS...")
        
        # Simular uma sexta-feira
        # Sexta 2024-01-26 -> +5 dias uteis -> Sexta 02/02
        start_date = date(2024, 1, 26) 
        prazo_dias = 5
        
        # Usando a função real do sistema
        due_date = calculate_due_date(start_date, prazo_dias, "dias uteis", self.servidor_id)
        
        # Verificação
        expected_date = date(2024, 2, 2) # Seg, Ter, Qua, Qui, Sex (5 dias)
        
        self.assertEqual(due_date, expected_date, 
                         f"Erro no cálculo de dias úteis. Esperado: {expected_date}, Obtido: {due_date}")
        print("   -> Cálculo dias úteis OK")

    def test_calculo_dias_corridos(self):
        """
        Teste 2: Valida se o cálculo de dias corridos inclui FDS.
        """
        print("\n[TEST] Verificando cálculo de DIAS CORRIDOS...")
        
        # Sexta 2024-01-26 -> +5 dias corridos -> Quarta 31/01
        start_date = date(2024, 1, 26) 
        prazo_dias = 5
        
        due_date = calculate_due_date(start_date, prazo_dias, "dias corridos", self.servidor_id)
        
        # Verificação
        expected_date = date(2024, 1, 31)
        
        self.assertEqual(due_date, expected_date, 
                         f"Erro no cálculo de dias corridos. Esperado: {expected_date}, Obtido: {due_date}")
        print("   -> Cálculo dias corridos OK")

    def test_alerta_vencimento(self):
        """
        Teste 3: Cria um processo com data retroativa para verificar se status fica 'Atrasado'
        NOTA: O status é calculado dinamicamente no frontend (Meus_Processos.py),
        mas aqui validamos se a data calculada de fato está no passado.
        """
        print("\n[TEST] Verificando detecção de ATRASO...")
        
        # Criar processo com atribuição há 20 dias atrás (prazo 5)
        data_passada = (date.today() - timedelta(days=20))
        
        processo_data = {
            "processo_numero": f"TEST-DELAY-{int(time.time())}",
            "id_tipo_produto": self.produto_dias_corridos['id'],
            "servidor_responsavel": "Teste Automatizado", 
            "id_servidor_responsavel": self.servidor_id,
            "data_entrada": data_passada.isoformat(),
            "data_atribuicao_servidor": data_passada.isoformat(),
            "prazo_servidor_aplicado": 5, # Venceu há 15 dias
            "status_servidor": "No Prazo", # Inicialmente diz "No Prazo"
            "status_chefe": "Aguardando Análise"
        }
        
        proc = insert("processos", processo_data)
        if proc:
            self.created_processes.append(proc['id'])
            
            # Recalcular data final usando a função do sistema
            data_final = calculate_due_date(
                data_passada, 
                5, 
                "dias corridos", 
                self.servidor_id
            )
            
            hoje = date.today()
            dias_atraso = (hoje - data_final).days
            
            print(f"   -> Processo criado em {data_passada}")
            print(f"   -> Data Vencimento Calculada: {data_final}")
            print(f"   -> Dias de atraso: {dias_atraso}")
            
            self.assertTrue(data_final < hoje, "A data final deveria ser menor que hoje (Vencido)")
            self.assertTrue(dias_atraso > 0, "Deveria ter dias de atraso positivos")
            print("   -> Lógica de atraso OK")

    def test_notificacao_criacao(self):
        """
        Teste 4: Verifica se notificações são realmente criadas no banco.
        """
        print("\n[TEST] Verificando criação de NOTIFICAÇÕES em banco...")
        
        msg = f"Teste de Notificação Automática {int(time.time())}"
        
        # Simular envio de notificação
        result = create_notification(self.servidor_id, msg)
        
        if result:
            self.created_notifications.append(result['id'])
            
            # Verificar se consegue ler de volta
            notificacoes = get_user_notifications(self.servidor_id, limit=5)
            found = False
            for n in notificacoes:
                if n['mensagem'] == msg:
                    found = True
                    # Validar status não lida
                    self.assertFalse(n['lida'], "Notificação deveria nascer como não-lida")
                    break
            
            self.assertTrue(found, "A notificação criada não foi encontrada na busca do usuário")
            print("   -> Sistema de notificações (Insert/Select) OK")
        else:
            self.fail("Falha ao criar notificação via create_notification()")

if __name__ == '__main__':
    unittest.main()
