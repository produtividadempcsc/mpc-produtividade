
import os
import sys
import unittest
from datetime import date, datetime, timedelta
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import QueryBuilder, insert, update_by_id, delete_by_id
from db_compat import (
    get_user_by_id, 
    get_process_by_id,
    update_process,
    create_substituicao,
    delete_substituicao,
    get_active_substitution
)

class TestPermissionsSubstitutions(unittest.TestCase):
    
    def setUp(self):
        """Setup: Criar Chefe e Servidor de teste + Processo"""
        self.created_data = {"users": [], "processes": [], "subs": []}
        
        # 1. Criar Chefe Fake
        chefe_data = {
            "nome_completo": f"Chefe Teste {int(time.time())}",
            "login": f"chefe.test.{int(time.time())}",
            "senha_hash": "hash_fake",
            "perfil": "Chefe de Gabinete",
            "email": "chefe@test.com",
            "ativo": True
        }
        self.chefe = insert("usuarios", chefe_data)
        self.created_data["users"].append(self.chefe['id'])
        
        # 2. Criar Servidor Fake
        import uuid
        servidor_data = {
            "nome_completo": f"Servidor Teste {int(time.time())}",
            "login": f"serv.test.{uuid.uuid4().hex[:8]}", # UUID para garantir unicidade
            "senha_hash": "hash_fake",
            "perfil": "Servidor",
            "email": f"serv.{uuid.uuid4().hex[:8]}@test.com",
            "ativo": True
        }
        self.servidor = insert("usuarios", servidor_data)
        if not self.servidor:
            self.fail("Falha ao criar Servidor fake")
        self.created_data["users"].append(self.servidor['id'])
        
        # 3. Criar Processo 
        processo_data = {
            "processo_numero": f"TEST-SEC-{uuid.uuid4().hex[:8]}",
            "id_tipo_produto": 1, 
            # REMOVIDO: servidor_responsavel (coluna string obsoleta)
            "id_servidor_responsavel": self.servidor['id'],
            "id_chefe_gabinete": self.chefe['id'],
            "status_servidor": "Concluído",
            "status_chefe": "Aguardando Análise",
            "data_atribuicao_servidor": date.today().isoformat()
        }
        self.processo = insert("processos", processo_data)
        if not self.processo:
            print(f"DEBUG - Erro dados processo: {processo_data}") # Debug extra
            self.fail("Falha ao criar Processo fake")
        self.created_data["processes"].append(self.processo['id'])

    def tearDown(self):
        """Limpeza"""
        print("\n[TEARDOWN] Limpando dados de segurança...")
        for sid in self.created_data["subs"]:
            delete_substituicao(sid)
        for pid in self.created_data["processes"]:
            delete_by_id("processos", pid)
        for uid in self.created_data["users"]:
            delete_by_id("usuarios", uid)

    def test_acesso_sem_substituicao(self):
        """
        Teste 1: Servidor TENTA aprovar processo sem ser substituto.
        Esperado: Falha de permissão (simulada via lógica de negócio).
        
        Nota: Como estamos testando o backend direto, verificamos a função
        `get_active_substitution`. Se ela retornar None, a UI bloquearia.
        """
        print("\n[TEST] Verificando acesso SEM substituição...")
        
        # Verificar se existe substituição ativa para o servidor
        sub = get_active_substitution(self.servidor['id'])
        
        if sub:
            self.fail("Não deveria haver substituição ativa neste momento!")
            
        print("   -> Servidor não tem substituição ativa (Bloqueio OK)")

    def test_fluxo_substituicao_completo(self):
        """
        Teste 2: Cria substituição e valida elevação de privilégio.
        """
        print("\n[TEST] Verificando fluxo de SUBSTITUIÇÃO...")
        
        # 1. Criar Substituição (Valida de Ontem até Amanhã)
        sub_data = {
            "id_chefe_titular": self.chefe['id'],
            "id_servidor_substituto": self.servidor['id'],
            "data_inicio": (date.today() - timedelta(days=1)).isoformat(),
            "data_fim": (date.today() + timedelta(days=1)).isoformat()
            # REMOVIDO: motivo (coluna inexistente)
        }
        
        nova_sub = create_substituicao(sub_data)
        if not nova_sub:
            self.fail("Falha ao criar substituição")
            
        self.created_data["subs"].append(nova_sub['id'])
        print(f"   -> Substituição criada (ID: {nova_sub['id']})")
        
        # 2. Verificar se o sistema reconhece a substituição agora
        active_sub = get_active_substitution(self.servidor['id'])
        
        self.assertIsNotNone(active_sub, "Sistema deveria retornar uma substituição ativa")
        self.assertEqual(active_sub['id_chefe_titular'], self.chefe['id'], 
                         "A substituição deve ser vinculada ao Chefe correto")
        
        print("   -> Sistema reconheceu a permissão elevada (Acesso OK)")
        
        # 3. Teste de Expiração (Mudar data fim para ontem)
        update_by_id("substituicoes", nova_sub['id'], {
            "data_fim": (date.today() - timedelta(days=1)).isoformat()
        })
        
        expired_sub = get_active_substitution(self.servidor['id'])
        self.assertIsNone(expired_sub, "Substituição expirada não deve dar acesso")
        
        print("   -> Expiração de permissão validada (Bloqueio OK)")

if __name__ == '__main__':
    unittest.main()
