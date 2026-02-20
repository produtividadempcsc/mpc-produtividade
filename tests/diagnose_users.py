"""Script de diagnóstico para verificar usuários e produtos."""
import sys
sys.path.insert(0, '.')

from db_compat import get_all_users, get_product_types

print("=== DIAGNÓSTICO DO BANCO ===\n")

# Usuários
users = get_all_users()
print(f"Total de usuários: {len(users)}")

servidores = [u for u in users if 'servidor' in u.get('perfil', '').lower()]
chefes = [u for u in users if 'chefe' in u.get('perfil', '').lower() or 'gabinete' in u.get('perfil', '').lower()]
procuradores = [u for u in users if 'procurador' in u.get('perfil', '').lower()]

print(f"\nServidores: {len(servidores)}")
for u in servidores[:3]:
    print(f"  - ID:{u.get('id')} | {u.get('nome_completo')} | Ativo:{u.get('ativo')}")

print(f"\nChefes de Gabinete: {len(chefes)}")
for u in chefes[:3]:
    print(f"  - ID:{u.get('id')} | {u.get('nome_completo')} | Ativo:{u.get('ativo')}")

print(f"\nProcuradores: {len(procuradores)}")
for u in procuradores[:3]:
    print(f"  - ID:{u.get('id')} | {u.get('nome_completo')} | Ativo:{u.get('ativo')}")

# Produtos
produtos = get_product_types()
print(f"\nTotal tipos de produto: {len(produtos)}")
for p in produtos[:5]:
    print(f"  - ID:{p.get('id')} | {p.get('nome_produto')} | Prazo Serv:{p.get('prazo_servidor')}")

print("\n=== FIM DIAGNÓSTICO ===")
