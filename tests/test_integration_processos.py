"""
Testes de Integração do Sistema de Processos MPCSC
===================================================
Este módulo automatiza testes de integração completos do sistema de processos,
simulando o fluxo entre Servidor, Chefe de Gabinete e Procurador.

Uso:
    python tests/test_integration_processos.py --count 10
    python tests/test_integration_processos.py --scenario basic_flow
    python tests/test_integration_processos.py --cleanup

Requisitos:
    - Variáveis de ambiente SUPABASE_URL e SUPABASE_KEY configuradas
    - Usuários de teste existentes no banco (ou usar --use-existing-users)
"""

import sys
import os
import argparse
import random
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import time

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import (
    supabase, QueryBuilder, insert, select_all, select_by_id, 
    update_by_id, delete_by_id
)
from db_compat import (
    get_process_by_id, get_user_by_id, update_process,
    add_process_history, create_notification, get_all_users,
    get_product_types
)
from test_data_generator import (
    generate_test_process_data, generate_batch_process_data,
    reset_counter, TEST_PREFIX, TEST_SCENARIOS, is_test_process
)


class TestResult:
    """Classe para armazenar resultado de um teste."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0.0
        self.details = {}
    
    def __repr__(self):
        status = "[PASS]" if self.passed else "[FAIL]"
        return f"{status} | {self.name} ({self.duration:.2f}s)"


class ProcessTestRunner:
    """
    Executor de testes de integração para o sistema de processos.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.created_processes: List[int] = []
        
        # Cache de usuários por perfil
        self._servidores = []
        self._chefes = []
        self._procuradores = []
        self._produtos = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log de mensagens se verbose ativo."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"INFO": "[INFO]", "SUCCESS": "[OK]", "ERROR": "[ERROR]", "WARNING": "[WARN]"}.get(level, "")
            print(f"[{timestamp}] {prefix} {message}")
    
    def load_users_and_products(self) -> bool:
        """
        Carrega usuários e produtos do banco para uso nos testes.
        Cria tipos de produto de teste se não houver suficientes.
        Retorna True se encontrou pelo menos um de cada tipo necessário.
        """
        self.log("Carregando usuários e tipos de produto do banco...")
        
        try:
            all_users = get_all_users()
            
            for user in all_users:
                if not user.get('ativo', True):
                    continue
                    
                perfil = user.get('perfil', '').lower()
                
                if 'servidor' in perfil:
                    self._servidores.append(user)
                elif 'chefe' in perfil or 'gabinete' in perfil:
                    self._chefes.append(user)
                elif 'procurador' in perfil:
                    self._procuradores.append(user)
            
            self._produtos = get_product_types()
            
            # Criar tipos de produto de teste se necessário (mínimo 5 tipos)
            if len(self._produtos) < 5:
                self.log("Criando tipos de produto de teste adicionais...", "WARNING")
                self._create_test_product_types()
                self._produtos = get_product_types()
            
            self.log(f"Encontrados: {len(self._servidores)} servidores, "
                    f"{len(self._chefes)} chefes, {len(self._procuradores)} procuradores, "
                    f"{len(self._produtos)} tipos de produto")
            
            if not self._servidores:
                self.log("ERRO: Nenhum servidor encontrado no banco!", "ERROR")
                return False
            if not self._chefes:
                self.log("ERRO: Nenhum chefe de gabinete encontrado no banco!", "ERROR")
                return False
            if not self._procuradores:
                self.log("ERRO: Nenhum procurador encontrado no banco!", "ERROR")
                return False
            if not self._produtos:
                self.log("ERRO: Nenhum tipo de produto encontrado no banco!", "ERROR")
                return False
                
            return True
            
        except Exception as e:
            self.log(f"Erro ao carregar dados: {e}", "ERROR")
            return False
    
    def _create_test_product_types(self):
        """Cria tipos de produto de teste para variar os cenários."""
        test_products = [
            {"nome_produto": "TEST - Parecer Simples", "prazo_servidor": 3, "prazo_chefe": 2, "tipo_contagem_prazo": "dias uteis"},
            {"nome_produto": "TEST - Parecer Complexo", "prazo_servidor": 10, "prazo_chefe": 5, "tipo_contagem_prazo": "dias uteis"},
            {"nome_produto": "TEST - Auditoria", "prazo_servidor": 15, "prazo_chefe": 7, "tipo_contagem_prazo": "dias uteis"},
            {"nome_produto": "TEST - Análise Técnica", "prazo_servidor": 5, "prazo_chefe": 3, "tipo_contagem_prazo": "dias corridos"},
            {"nome_produto": "TEST - Manifestação", "prazo_servidor": 7, "prazo_chefe": 4, "tipo_contagem_prazo": "dias uteis"},
            {"nome_produto": "TEST - Relatório", "prazo_servidor": 20, "prazo_chefe": 10, "tipo_contagem_prazo": "dias uteis"},
        ]
        
        # Gerar um ID base alto para evitar colisões
        base_nome_id = 9000
        
        for i, product_data in enumerate(test_products):
            try:
                # Verificar se já existe
                existing = QueryBuilder("tipos_produto").eq("nome_produto", product_data["nome_produto"]).execute()
                if not existing:
                    product_data["versao"] = 1
                    product_data["data_criacao"] = datetime.now().isoformat()
                    # Gerar nome_id único para teste (necessário por constraint)
                    product_data["nome_id"] = base_nome_id + i
                    insert("tipos_produto", product_data)
                    self.log(f"  Criado tipo de produto: {product_data['nome_produto']}", "SUCCESS")
            except Exception as e:
                self.log(f"  Erro ao criar tipo {product_data['nome_produto']}: {e}", "ERROR")
        

    
    def create_process(self, config: Dict = None) -> Optional[int]:
        """
        Cria um processo de teste no banco.
        
        Args:
            config: Configurações opcionais para sobrescrever dados padrão
            
        Returns:
            ID do processo criado ou None em caso de erro
        """
        config = config or {}
        
        # Seleção aleatória para melhor cobertura de teste
        servidor = random.choice(self._servidores)
        chefe = random.choice(self._chefes)
        procurador = random.choice(self._procuradores)
        produto = random.choice(self._produtos)
        
        processo_data = generate_test_process_data(
            servidor_id=servidor['id'],
            chefe_id=chefe['id'],
            procurador_id=procurador['id'],
            tipo_produto_id=produto['id'],
            prazo_servidor=produto.get('prazo_servidor', 5),
            prazo_chefe=produto.get('prazo_chefe', 3),
            **config
        )
        
        try:
            result = insert("processos", processo_data)
            
            if result:
                processo_id = result['id']
                self.created_processes.append(processo_id)
                self.log(f"Processo criado: {processo_data['processo_numero']} (ID: {processo_id})", "SUCCESS")
                return processo_id
            else:
                self.log("Falha ao inserir processo no banco", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Erro ao criar processo: {e}", "ERROR")
            return None
    
    def simulate_servidor_conclusion(self, processo_id: int) -> bool:
        """
        Simula a conclusão de um processo pelo servidor.
        
        Args:
            processo_id: ID do processo
            
        Returns:
            True se sucesso
        """
        processo = get_process_by_id(processo_id)
        if not processo:
            self.log(f"Processo {processo_id} não encontrado", "ERROR")
            return False
        
        updates = {
            "data_conclusao_servidor": date.today().isoformat(),
            "status_servidor": "Concluído"
        }
        
        # Verificar flags de exceção
        if processo.get('ignorar_revisao_chefe'):
            updates["status_chefe"] = "Processo com o Procurador"
            if processo.get('ignorar_analise_procurador'):
                updates["status_chefe"] = "Finalizado"
                updates["status_servidor"] = "Finalizado"
        else:
            updates["status_chefe"] = "Aguardando Análise"
        
        try:
            update_process(processo_id, updates)
            
            # Adicionar ao histórico
            add_process_history(
                processo_id,
                processo.get('id_servidor_responsavel'),
                "Concluído pelo Servidor",
                "Teste automatizado"
            )
            
            self.log(f"Processo {processo_id}: Servidor concluiu -> status={updates['status_servidor']}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Erro ao simular conclusão do servidor: {e}", "ERROR")
            return False
    
    def simulate_chefe_approval(self, processo_id: int) -> bool:
        """
        Simula a aprovação do processo pelo chefe de gabinete.
        
        Args:
            processo_id: ID do processo
            
        Returns:
            True se sucesso
        """
        processo = get_process_by_id(processo_id)
        if not processo:
            self.log(f"Processo {processo_id} não encontrado", "ERROR")
            return False
        
        updates = {
            "data_conclusao_chefe": date.today().isoformat()
        }
        
        if processo.get('ignorar_analise_procurador'):
            updates["status_chefe"] = "Finalizado"
            updates["status_servidor"] = "Finalizado"
        else:
            updates["status_chefe"] = "Processo com o Procurador"
        
        try:
            update_process(processo_id, updates)
            
            add_process_history(
                processo_id,
                processo.get('id_chefe_gabinete'),
                "Aprovado pelo Chefe de Gabinete",
                "Teste automatizado"
            )
            
            self.log(f"Processo {processo_id}: Chefe aprovou -> status={updates['status_chefe']}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Erro ao simular aprovação do chefe: {e}", "ERROR")
            return False
    
    def simulate_chefe_return(self, processo_id: int, observacao: str = "Devolução de teste") -> bool:
        """
        Simula a devolução do processo pelo chefe ao servidor.
        
        Args:
            processo_id: ID do processo
            observacao: Observação da devolução
            
        Returns:
            True se sucesso
        """
        processo = get_process_by_id(processo_id)
        if not processo:
            self.log(f"Processo {processo_id} não encontrado", "ERROR")
            return False
        
        updates = {
            "status_servidor": "Devolvido",
            "status_chefe": "Devolvido",
            "data_conclusao_servidor": None,
            "data_atribuicao_servidor": date.today().isoformat(),
            "prazo_servidor_aplicado": 5,  # Novo prazo
            "observacao_chefe": observacao
        }
        
        try:
            update_process(processo_id, updates)
            
            add_process_history(
                processo_id,
                processo.get('id_chefe_gabinete'),
                "Devolvido pelo Chefe de Gabinete",
                observacao
            )
            
            # Adicionar comentário
            insert("comentarios", {
                "id_processo": processo_id,
                "id_usuario": processo.get('id_chefe_gabinete'),
                "texto": f"PROCESSO DEVOLVIDO: {observacao}",
                "timestamp": datetime.now().isoformat()
            })
            
            self.log(f"Processo {processo_id}: Chefe devolveu -> status=Devolvido", "WARNING")
            return True
            
        except Exception as e:
            self.log(f"Erro ao simular devolução do chefe: {e}", "ERROR")
            return False
    
    def simulate_procurador_finalization(self, processo_id: int) -> bool:
        """
        Simula a finalização do processo pelo procurador.
        
        Args:
            processo_id: ID do processo
            
        Returns:
            True se sucesso
        """
        processo = get_process_by_id(processo_id)
        if not processo:
            self.log(f"Processo {processo_id} não encontrado", "ERROR")
            return False
        
        updates = {
            "status_chefe": "Finalizado",
            "status_servidor": "Finalizado"
        }
        
        try:
            update_process(processo_id, updates)
            
            add_process_history(
                processo_id,
                processo.get('id_procurador'),
                "Finalizado pelo Procurador",
                "Teste automatizado"
            )
            
            self.log(f"Processo {processo_id}: Procurador finalizou -> status=Finalizado", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Erro ao simular finalização do procurador: {e}", "ERROR")
            return False
    
    def validate_process_state(self, processo_id: int, expected: Dict) -> Tuple[bool, str]:
        """
        Valida o estado atual de um processo contra o esperado.
        
        Args:
            processo_id: ID do processo
            expected: Dicionário com campos e valores esperados
            
        Returns:
            Tupla (sucesso, mensagem)
        """
        processo = get_process_by_id(processo_id)
        if not processo:
            return False, f"Processo {processo_id} não encontrado"
        
        errors = []
        for field, expected_value in expected.items():
            actual_value = processo.get(field)
            if actual_value != expected_value:
                errors.append(f"{field}: esperado '{expected_value}', obteve '{actual_value}'")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "OK"
    
    def run_scenario(self, scenario_name: str) -> TestResult:
        """
        Executa um cenário de teste pré-definido.
        
        Args:
            scenario_name: Nome do cenário (ver TEST_SCENARIOS)
            
        Returns:
            TestResult com o resultado do teste
        """
        result = TestResult(f"Scenario: {scenario_name}")
        start_time = time.time()
        
        if scenario_name not in TEST_SCENARIOS:
            result.error = f"Cenário desconhecido: {scenario_name}"
            result.duration = time.time() - start_time
            return result
        
        scenario = TEST_SCENARIOS[scenario_name]
        config = scenario.get('config', {})
        steps = scenario.get('steps', [])
        
        self.log(f"\n{'='*60}")
        self.log(f"Executando cenário: {scenario_name}")
        self.log(f"Descrição: {scenario.get('description', 'N/A')}")
        self.log(f"{'='*60}")
        
        processo_id = None
        
        try:
            for step in steps:
                self.log(f"  > Executando passo: {step}")
                
                if step == "create":
                    processo_id = self.create_process(config)
                    if not processo_id:
                        raise Exception("Falha ao criar processo")
                        
                elif step == "servidor_conclude":
                    if not self.simulate_servidor_conclusion(processo_id):
                        raise Exception("Falha na conclusão do servidor")
                        
                elif step == "chefe_approve":
                    if not self.simulate_chefe_approval(processo_id):
                        raise Exception("Falha na aprovação do chefe")
                        
                elif step == "chefe_return":
                    if not self.simulate_chefe_return(processo_id):
                        raise Exception("Falha na devolução do chefe")
                        
                elif step == "procurador_finalize":
                    if not self.simulate_procurador_finalization(processo_id):
                        raise Exception("Falha na finalização do procurador")
                
                else:
                    self.log(f"  [WARN] Passo desconhecido: {step}", "WARNING")
            
            # Validar estado final
            processo_final = get_process_by_id(processo_id)
            result.details['processo_id'] = processo_id
            result.details['status_final'] = {
                'servidor': processo_final.get('status_servidor'),
                'chefe': processo_final.get('status_chefe')
            }
            
            result.passed = True
            self.log(f"Cenário {scenario_name} concluído com sucesso!", "SUCCESS")
            
        except Exception as e:
            result.error = str(e)
            result.details['processo_id'] = processo_id
            self.log(f"Cenário {scenario_name} falhou: {e}", "ERROR")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        return result
    
    def run_batch_test(self, count: int = 10) -> List[TestResult]:
        """
        Executa testes em batch criando múltiplos processos.
        
        Args:
            count: Número de processos a criar
            
        Returns:
            Lista de TestResults
        """
        self.log(f"\n{'='*60}")
        self.log(f"Executando teste em batch: {count} processos")
        self.log(f"{'='*60}")
        
        result = TestResult(f"Batch Test ({count} processos)")
        start_time = time.time()
        
        try:
            # Gerar dados em batch
            batch_data = generate_batch_process_data(
                self._servidores,
                self._chefes,
                self._procuradores,
                self._produtos,
                count=count
            )
            
            created = 0
            errors = 0
            
            for processo_data in batch_data:
                try:
                    res = insert("processos", processo_data)
                    if res and res.data:
                        self.created_processes.append(res.data[0]['id'])
                        created += 1
                    else:
                        errors += 1
                except Exception as e:
                    errors += 1
                    self.log(f"Erro ao inserir processo: {e}", "ERROR")
            
            result.details = {
                'total': count,
                'created': created,
                'errors': errors
            }
            
            result.passed = (created == count)
            
            if result.passed:
                self.log(f"Batch concluído: {created}/{count} processos criados", "SUCCESS")
            else:
                self.log(f"Batch com erros: {created}/{count} processos criados", "WARNING")
            
        except Exception as e:
            result.error = str(e)
            self.log(f"Erro no batch test: {e}", "ERROR")
        
        result.duration = time.time() - start_time
        self.results.append(result)
        return [result]
    
    def run_stress_test(self, count: int = 50) -> Tuple[int, int]:
        """
        Executa múltiplos cenários aleatórios para testar o sistema.
        
        Args:
            count: Número de execuções
            
        Returns:
            Tupla (passou, falhou)
        """
        self.log(f"\n{'='*60}")
        self.log(f"Executando STRESS TEST: {count} cenários aleatórios")
        self.log(f"{'='*60}")
        
        scenarios_keys = list(TEST_SCENARIOS.keys())
        passed = 0
        failed = 0
        
        for i in range(count):
            scenario_name = random.choice(scenarios_keys)
            self.log(f"\n--- Execução {i+1}/{count}: {scenario_name} ---")
            
            result = self.run_scenario(scenario_name)
            
            if result.passed:
                passed += 1
            else:
                failed += 1
                
        self.log(f"\nStress Test concluído: {passed} sucessos, {failed} falhas", "INFO")
        return passed, failed

    def cleanup_test_data(self) -> int:
        """
        Remove todos os processos de teste criados.
        
        Returns:
            Número de processos removidos
        """
        self.log("\n🧹 Limpando dados de teste...")
        
        removed = 0
        
        # Remover processos criados nesta sessão
        for processo_id in self.created_processes:
            try:
                # Remover histórico primeiro
                QueryBuilder("processo_historico").eq("id_processo", processo_id).delete()
                
                # Remover comentários
                QueryBuilder("comentarios").eq("id_processo", processo_id).delete()
                
                # Remover favoritos
                QueryBuilder("processo_favoritos").eq("id_processo", processo_id).delete()
                
                # Remover anexos
                QueryBuilder("anexos_processo").eq("id_processo", processo_id).delete()
                
                # Remover processo
                delete_by_id("processos", processo_id)
                removed += 1
                
            except Exception as e:
                self.log(f"Erro ao remover processo {processo_id}: {e}", "ERROR")
        
        self.log(f"Removidos {removed} processos de teste", "SUCCESS")
        
        # Limpar lista
        self.created_processes = []
        
        return removed
    
    def cleanup_all_test_processes(self) -> int:
        """
        Remove TODOS os processos de teste do banco (com prefixo TEST-).
        
        Returns:
            Número de processos removidos
        """
        self.log("\n🧹 Removendo TODOS os processos de teste do banco...")
        
        try:
            # Buscar processos com prefixo de teste
            test_processes = QueryBuilder("processos") \
                .like("processo_numero", f"{TEST_PREFIX}-%") \
                .execute()
            
            removed = 0
            total = len(test_processes)
            
            self.log(f"Encontrados {total} processos de teste para remoção")
            
            for processo in test_processes:
                processo_id = processo['id']
                
                try:
                    # Remover dependências
                    QueryBuilder("processo_historico").eq("id_processo", processo_id).delete()
                    QueryBuilder("comentarios").eq("id_processo", processo_id).delete()
                    QueryBuilder("processo_favoritos").eq("id_processo", processo_id).delete()
                    QueryBuilder("anexos_processo").eq("id_processo", processo_id).delete()
                    
                    # Remover processo
                    delete_by_id("processos", processo_id)
                    removed += 1
                    
                except Exception as e:
                    self.log(f"Erro ao remover processo {processo_id}: {e}", "ERROR")
            
            self.log(f"Removidos {removed}/{total} processos de teste", "SUCCESS")
            return removed
            
        except Exception as e:
            self.log(f"Erro durante limpeza: {e}", "ERROR")
            return 0
    
    def print_summary(self):
        """Imprime resumo dos testes executados."""
        print("\n" + "="*60)
        print("\nRESUMO DOS TESTES")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        print(f"Total: {total} | Passou: {passed} | Falhou: {failed}")
        print("-"*60)
        
        for result in self.results:
            print(result)
            if result.error:
                print(f"    Erro: {result.error}")
            if result.details:
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
        
        print("="*60)
        
        return passed, failed


def main():
    """Função principal do script de testes."""
    parser = argparse.ArgumentParser(
        description='Script de Testes de Integração - Sistema de Processos MPCSC'
    )
    parser.add_argument(
        '--count', '-c',
        type=int,
        default=5,
        help='Número de processos para criar no batch test (default: 5)'
    )
    parser.add_argument(
        '--scenario', '-s',
        type=str,
        choices=list(TEST_SCENARIOS.keys()),
        help='Executar um cenário específico'
    )
    parser.add_argument(
        '--all-scenarios', '-a',
        action='store_true',
        help='Executar todos os cenários de teste'
    )
    parser.add_argument(
        '--cleanup', '-x',
        action='store_true',
        help='Remover todos os processos de teste do banco'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Não remover processos de teste ao final'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso (menos output)'
    )
    
    parser.add_argument(
        '--stress-test',
        type=int,
        help='Executar N cenários aleatórios (Stress Test)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("TESTES DE INTEGRACAO - SISTEMA DE PROCESSOS MPCSC")
    print("="*60)
    
    runner = ProcessTestRunner(verbose=not args.quiet)
    
    # Apenas limpeza?
    if args.cleanup:
        runner.cleanup_all_test_processes()
        return
    
    # Carregar usuários e produtos
    if not runner.load_users_and_products():
        print("\n❌ Falha ao carregar dados do banco. Verifique a configuração do Supabase.")
        sys.exit(1)
    
    # Executar testes
    if args.stress_test:
        reset_counter()
        runner.run_stress_test(args.stress_test)
        
    elif args.all_scenarios:
        reset_counter()
        for scenario_name in TEST_SCENARIOS.keys():
            runner.run_scenario(scenario_name)
            
    elif args.scenario:
        reset_counter()
        runner.run_scenario(args.scenario)
        
    else:
        # Batch test padrão
        reset_counter()
        runner.run_batch_test(args.count)
    
    # Imprimir resumo
    passed, failed = runner.print_summary()
    
    # Limpeza automática (a menos que --no-cleanup)
    if not args.no_cleanup:
        runner.cleanup_test_data()
    else:
        print(f"\n[WARN] {len(runner.created_processes)} processos de teste mantidos no banco.")
        print(f"   Para limpar depois: python {__file__} --cleanup")
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
