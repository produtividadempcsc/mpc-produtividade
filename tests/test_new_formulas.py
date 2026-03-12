
import unittest
import pandas as pd
from datetime import timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import analytics_utils

# Mock utils functions to avoid DB calls
# We need to mock calculate_net_work_days_batch, calculate_net_duration_calendar_batch, calculate_due_date_batch
# Let's mock them in prazo_service

class TestNewFormulas(unittest.TestCase):
    
    def setUp(self):
        # Mocking the underlying utility functions to behave deterministically for tests
        # This avoids dependency on real holidays/leaves/DB
        
        # Mock calculate_net_work_days_batch: returns (end - start).days - 2 (simulating weekend)
        self.original_net_work = analytics_utils.calculate_net_work_days_batch
        analytics_utils.calculate_net_work_days_batch = lambda s, e, a, f: max(0, (e - s).days - 2)
        
        # Mock calculate_net_duration_calendar_batch: returns (end - start).days + 1 - 0 (no leaves) - suspension
        self.original_net_calendar = analytics_utils.calculate_net_duration_calendar_batch
        analytics_utils.calculate_net_duration_calendar_batch = lambda s, e, a, susp: max(0, (e - s).days + 1 - susp)
        
        # Mock calculate_due_date_batch: returns start + prazo (simple)
        self.original_due_date = analytics_utils.calculate_due_date_batch
        # Note: Argument names must match those used in analytics_utils.py call
        analytics_utils.calculate_due_date_batch = lambda start_date, prazo_dias, tipo_contagem, afastamentos_datas, feriados, dias_suspensos: start_date + timedelta(days=prazo_dias+dias_suspensos)

        self.original_prefetch = analytics_utils._prefetch_batch_data
        analytics_utils._prefetch_batch_data = lambda df: (set(), {})

    def tearDown(self):
        # Restore originals
        analytics_utils.calculate_net_work_days_batch = self.original_net_work
        analytics_utils.calculate_net_duration_calendar_batch = self.original_net_calendar
        analytics_utils.calculate_due_date_batch = self.original_due_date
        analytics_utils._prefetch_batch_data = self.original_prefetch

    def test_duration_metrics_servidor(self):
        # Data Setup
        data = [{
            'id_servidor_responsavel': 1,
            'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
            'data_conclusao_servidor': pd.Timestamp('2024-01-10'), # 9 days diff
            'tipo_contagem_prazo': 'dias uteis',
            'prazo_total_dias_suspenso': 1,
            'prazo_servidor_aplicado': 10
        }, {
            'id_servidor_responsavel': 1,
            'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
            'data_conclusao_servidor': pd.Timestamp('2024-01-10'),
            'tipo_contagem_prazo': 'dias corridos',
            'prazo_total_dias_suspenso': 2,
            'prazo_servidor_aplicado': 10
        }]
        df = pd.DataFrame(data)
        
        # Run
        res = analytics_utils.calculate_metrics_servidor(df)
        
        # Row 0: Dias Uteis
        # logic: max(0, net_work - susp)
        # net_work mock: (10-1) - 2 = 7
        # susp = 1
        # result = 6
        self.assertEqual(res.iloc[0]['duracao_servidor'], 6)
        
        # Row 1: Dias Corridos
        # logic: net_calendar (which handles susp inside)
        # net_calendar mock: (10-1) + 1 - 2 = 8
        # result = 8
        self.assertEqual(res.iloc[1]['duracao_servidor'], 8)
        
        # Check deadline (no_prazo)
        # Row 0: due date = start (Jan 1) + 10 + 1 = Jan 12
        # Conclusao Jan 10 <= Jan 12 -> True
        self.assertTrue(res.iloc[0]['no_prazo_servidor'])


    def test_acervo_snapshot(self):
        # Data Setup
        ref_date = pd.Timestamp('2024-01-15')
        
        data = [
            # 1. Normal Pending (Received before ref, not finished) -> Should be IN
            {
                'id': 1,
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'data_conclusao_servidor': pd.NaT,
                'status_servidor': 'Em Andamento',
                'nao_se_aplica_prazo_servidor': False
            },
            # 2. Finished before ref -> Should be OUT
            {
                'id': 2,
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'data_conclusao_servidor': pd.Timestamp('2024-01-10'),
                'status_servidor': 'Concluído',
                'nao_se_aplica_prazo_servidor': False
            },
            # 3. Finished AFTER ref -> Should be OUT (logic uses current Status which is Concluído)
            # NOTE: relatorios.py excludes completed items even if completed after ref date if driven by status
            {
                'id': 3,
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'data_conclusao_servidor': pd.Timestamp('2024-01-20'),
                'status_servidor': 'Concluído', # Current status in DB
                'nao_se_aplica_prazo_servidor': False
            },
            # 4. Devolved (status 'Devolvido') -> Should be IN
            {
                'id': 4,
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'data_conclusao_servidor': pd.Timestamp('2024-01-10'), # Was finished once
                'status_servidor': 'Devolvido', # But sent back
                'nao_se_aplica_prazo_servidor': False
            },
            # 5. Skipped Phase -> Should be OUT
            {
                'id': 5,
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'data_conclusao_servidor': pd.NaT,
                'status_servidor': 'Em Andamento',
                'nao_se_aplica_prazo_servidor': True
            }
        ]
        
        # Add Chefe columns for context (avoid key errors if any)
        for d in data:
            d.update({
                'data_conclusao_chefe': pd.NaT,
                'status_chefe': 'Aguardando',
                'ignorar_revisao_chefe': False
            })

            
        df = pd.DataFrame(data)
        
        # Run
        serv_acervo, _ = analytics_utils.calculate_acervo_snapshot(df, ref_date)
        
        ids_in_acervo = sorted(serv_acervo['id'].tolist())
        # Metric 4 logic excludes Concluído status, so 3 is out.
        expected_ids = [1, 4]
        
        self.assertEqual(ids_in_acervo, expected_ids)

    def test_acervo_chefe_snapshot(self):
        ref_date = pd.Timestamp('2024-01-15')
        
        data = [
            # 1. Server Finished before ref, Chefe Pending -> IN
            {
                'id': 1,
                'data_conclusao_servidor': pd.Timestamp('2024-01-10'),
                'data_conclusao_chefe': pd.NaT,
                'status_chefe': 'Aguardando Análise',
                'ignorar_revisao_chefe': False
            },
            # 2. Server Finished AFTER ref -> OUT (Not in Chefe queue yet)
            {
                'id': 2,
                'data_conclusao_servidor': pd.Timestamp('2024-01-20'),
                'data_conclusao_chefe': pd.NaT,
                'status_chefe': 'Aguardando Análise',
                'ignorar_revisao_chefe': False
            },
            # 3. Chefe Devolved -> IN
            {
                'id': 3,
                'data_conclusao_servidor': pd.Timestamp('2024-01-10'),
                'data_conclusao_chefe': pd.Timestamp('2024-01-12'), # Was finished
                'status_chefe': 'Devolvido', # Sent back by Procurador
                'ignorar_revisao_chefe': False
            },
            # 4. Skipped -> OUT
            {
                'id': 4,
                'data_conclusao_servidor': pd.Timestamp('2024-01-10'),
                'data_conclusao_chefe': pd.NaT,
                'status_chefe': 'Aguardando Análise',
                'ignorar_revisao_chefe': True
            }
        ]
        
        # Fill required columns for ACERVO SERV logic (to avoid errors if function checks them)
        for d in data:
            d.update({
                'data_atribuicao_servidor': pd.Timestamp('2024-01-01'),
                'status_servidor': 'Concluído',
                'nao_se_aplica_prazo_servidor': False
            })

        df = pd.DataFrame(data)
        
        _, chefe_acervo = analytics_utils.calculate_acervo_snapshot(df, ref_date)
        
        ids_in = sorted(chefe_acervo['id'].tolist())
        expected = [1, 3] # 1 is pending, 3 is devolved.
        
        self.assertEqual(ids_in, expected)

if __name__ == '__main__':
    unittest.main()
