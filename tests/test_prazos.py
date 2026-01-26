import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import sys
import os

# Adicionar diretório pai ao path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_compat import calculate_due_date

class TestCalculoPrazos(unittest.TestCase):

    @patch('services.prazo_service.get_all_holidays')
    @patch('services.prazo_service.get_leave_dates_set')
    def test_prazo_dias_uteis_simples(self, mock_leaves, mock_holidays):
        """Testa prazo de 1 dia útil começando numa sexta-feira."""
        # Setup mocks
        mock_holidays.return_value = set()
        mock_leaves.return_value = set()
        
        # Sexta-feira
        start_date = date(2023, 10, 6) 
        # Prazo 1 dia útil -> deve cair na Segunda-feira (09/10)
        
        due_date = calculate_due_date(start_date, 1, "dias uteis", 1)
        
        self.assertEqual(due_date, date(2023, 10, 9))

    @patch('services.prazo_service.get_all_holidays')
    @patch('services.prazo_service.get_leave_dates_set')
    def test_prazo_dias_uteis_com_feriado(self, mock_leaves, mock_holidays):
        """Testa prazo com feriado na segunda-feira."""
        # Segunda-feira é feriado
        mock_holidays.return_value = {date(2023, 10, 9)}
        mock_leaves.return_value = set()
        
        # Sexta-feira
        start_date = date(2023, 10, 6)
        # Prazo 1 dia útil -> Segunda é feriado -> Terça (10/10)
        
        due_date = calculate_due_date(start_date, 1, "dias uteis", 1)
        
        self.assertEqual(due_date, date(2023, 10, 10))

    @patch('services.prazo_service.get_all_holidays')
    @patch('services.prazo_service.get_leave_dates_set')
    def test_prazo_dias_corridos(self, mock_leaves, mock_holidays):
        """Testa prazo em dias corridos (inclui fim de semana)."""
        mock_holidays.return_value = set()
        mock_leaves.return_value = set()
        
        # Sexta-feira
        start_date = date(2023, 10, 6)
        # Prazo 2 dias corridos -> Domingo (08/10)
        
        due_date = calculate_due_date(start_date, 2, "dias corridos", 1)
        
        self.assertEqual(due_date, date(2023, 10, 8))

    @patch('services.prazo_service.get_all_holidays')
    @patch('services.prazo_service.get_leave_dates_set')
    def test_prazo_com_suspensao(self, mock_leaves, mock_holidays):
        """Testa adição de dias de suspensão."""
        mock_holidays.return_value = set()
        mock_leaves.return_value = set()
        
        # Segunda-feira
        start_date = date(2023, 10, 2)
        # Prazo 1 dia útil -> Terça (03/10)
        # + 2 dias de suspensão -> Quinta (05/10)
        
        # Nota: A lógica exata de suspensão depende da implementação. 
        # Se suspensão for em dias úteis ou corridos. Assumindo que estende o prazo.
        # Vamos verificar se a função trata suspensão apenas adicionando dias ao final.
        
        due_date = calculate_due_date(start_date, 1, "dias uteis", 1, dias_suspensos=2)
        
        self.assertEqual(due_date, date(2023, 10, 5))

    @patch('services.prazo_service.get_all_holidays')
    @patch('services.prazo_service.get_leave_dates_set')
    def test_prazo_com_afastamento_usuario(self, mock_leaves, mock_holidays):
        """Testa se afatamento do usuário adia o prazo."""
        mock_holidays.return_value = set()
        # Usuário afastado na terça-feira (03/10)
        mock_leaves.return_value = {date(2023, 10, 3)}
        
        # Segunda-feira
        start_date = date(2023, 10, 2)
        # Prazo 2 dias úteis
        # Dia 1: Terça (Afastado - não conta)
        # Dia 1: Quarta (04/10) - Conta
        # Dia 2: Quinta (05/10) - Conta
        # Wait, se afastado não conta, pula o dia.
        # Start(02) -> +1 -> 03 (afastado) -> +1 -> 04 (ok, count=1) -> +1 -> 05 (ok, count=2)
        # Final deve ser 05/10?
        # Vamos verificar a lógica do while loop no db_compat.
        
        due_date = calculate_due_date(start_date, 2, "dias uteis", 1)
        
        self.assertEqual(due_date, date(2023, 10, 5))

if __name__ == '__main__':
    unittest.main()
