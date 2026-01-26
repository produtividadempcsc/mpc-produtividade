"""
Supabase Client - Singleton para conexão com Supabase via REST API
===================================================================
Este módulo substitui a conexão direta PostgreSQL por chamadas REST HTTPS,
resolvendo problemas de IPv4/IPv6.
"""

import os
from dotenv import load_dotenv

# Carregar .env
load_dotenv(override=True)

# Configurações do Supabase
SUPABASE_URL = None
SUPABASE_KEY = None

# Tentar ler do Streamlit secrets primeiro
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        SUPABASE_URL = st.secrets.get("SUPABASE_URL")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
        if SUPABASE_URL:
            print("[SUPABASE] Usando configuração do Streamlit secrets")
except Exception as e:
    print(f"[SUPABASE] Streamlit secrets não disponível: {e}")

# Fallback para variáveis de ambiente
if not SUPABASE_URL:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ufdbeitzqjfzyvmctcyn.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    if SUPABASE_KEY:
        print("[SUPABASE] Usando configuração do .env")

# Validar configuração
if not SUPABASE_KEY:
    print("[SUPABASE] AVISO: SUPABASE_KEY não configurada!")

# Inicializar cliente Supabase
supabase = None

try:
    from supabase import create_client, Client
    
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[SUPABASE] Cliente inicializado com sucesso para {SUPABASE_URL}")
    else:
        print("[SUPABASE] ERRO: Impossível criar cliente - credenciais ausentes")
except ImportError as e:
    print(f"[SUPABASE] ERRO: Biblioteca supabase não instalada: {e}")
except Exception as e:
    print(f"[SUPABASE] ERRO ao criar cliente: {e}")


def get_supabase() -> Client:
    """
    Retorna o cliente Supabase singleton.
    Usado em substituição ao get_db() do SQLAlchemy.
    """
    global supabase
    if supabase is None:
        print("[SUPABASE] ERRO CRÍTICO: Tentativa de uso do cliente sem inicialização.")
        raise RuntimeError(
            "Cliente Supabase não inicializado. "
            "Verifique se as variáveis SUPABASE_URL e SUPABASE_KEY estão configuradas no .env ou Secrets."
        )
    return supabase

def is_client_initialized() -> bool:
    """Retorna True se o cliente Supabase estiver inicializado corretamente."""
    return supabase is not None


# ============================================================================
# HELPER FUNCTIONS - Operações comuns de banco de dados
# ============================================================================

def select_all(table: str, columns: str = "*"):
    """
    Seleciona todos os registros de uma tabela.
    
    Args:
        table: Nome da tabela
        columns: Colunas a selecionar (ex: "id, nome" ou "*")
    
    Returns:
        Lista de dicionários com os registros
    """
    try:
        result = supabase.table(table).select(columns).execute()
        return result.data
    except Exception as e:
        print(f"[SUPABASE] Erro ao selecionar de {table}: {e}")
        return []


def select_by_id(table: str, id: int, columns: str = "*"):
    """
    Seleciona um registro por ID.
    
    Returns:
        Dicionário com o registro ou None
    """
    try:
        result = supabase.table(table).select(columns).eq("id", id).single().execute()
        return result.data
    except Exception as e:
        print(f"[SUPABASE] Erro ao buscar {table} id={id}: {e}")
        return None


def select_where(table: str, column: str, value, columns: str = "*"):
    """
    Seleciona registros com filtro simples.
    
    Returns:
        Lista de dicionários
    """
    try:
        result = supabase.table(table).select(columns).eq(column, value).execute()
        return result.data
    except Exception as e:
        print(f"[SUPABASE] Erro ao filtrar {table}: {e}")
        return []


def select_first(table: str, column: str, value, columns: str = "*"):
    """
    Seleciona o primeiro registro que match o filtro.
    
    Returns:
        Dicionário ou None
    """
    try:
        result = supabase.table(table).select(columns).eq(column, value).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SUPABASE] Erro ao buscar primeiro de {table}: {e}")
        return None


def insert(table: str, data: dict):
    """
    Insere um registro.
    
    Returns:
        Dicionário do registro inserido ou None
    """
    try:
        result = supabase.table(table).insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SUPABASE] Erro ao inserir em {table}: {e}")
        return None


def upsert(table: str, data: dict):
    """
    Insere ou atualiza um registro (upsert).
    
    Returns:
        Dicionário do registro inserido/atualizado ou None
    """
    try:
        result = supabase.table(table).upsert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SUPABASE] Erro ao upsert em {table}: {e}")
        return None


def update_by_id(table: str, id: int, data: dict):
    """
    Atualiza um registro por ID.
    
    Returns:
        Dicionário do registro atualizado ou None
    """
    try:
        result = supabase.table(table).update(data).eq("id", id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SUPABASE] Erro ao atualizar {table} id={id}: {e}")
        return None


def delete_by_id(table: str, id: int):
    """
    Deleta um registro por ID.
    
    Returns:
        True se deletado, False caso contrário
    """
    try:
        result = supabase.table(table).delete().eq("id", id).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE] Erro ao deletar {table} id={id}: {e}")
        return False


def count(table: str, column: str = None, value = None):
    """
    Conta registros de uma tabela, opcionalmente com filtro.
    
    Returns:
        Número de registros
    """
    try:
        query = supabase.table(table).select("*", count="exact")
        if column and value is not None:
            query = query.eq(column, value)
        result = query.execute()
        return result.count if result.count is not None else len(result.data)
    except Exception as e:
        print(f"[SUPABASE] Erro ao contar {table}: {e}")
        return 0


# ============================================================================
# QUERY BUILDER - Para queries mais complexas
# ============================================================================

class QueryBuilder:
    """
    Builder para queries complexas, similar ao SQLAlchemy query.
    
    Exemplo:
        users = QueryBuilder("usuarios") \
            .select("id, nome_completo, perfil") \
            .eq("perfil", "Servidor") \
            .order("nome_completo") \
            .execute()
    """
    
    def __init__(self, table: str):
        self.table_name = table
        self._columns = "*"
        self._filters = []
        self._order_column = None
        self._order_desc = False
        self._limit_val = None
        self._offset_val = None
    
    def select(self, columns: str = "*"):
        """Define colunas a selecionar."""
        self._columns = columns
        return self
    
    def eq(self, column: str, value):
        """Filtro de igualdade."""
        self._filters.append(("eq", column, value))
        return self
    
    def neq(self, column: str, value):
        """Filtro de diferença."""
        self._filters.append(("neq", column, value))
        return self
    
    def gt(self, column: str, value):
        """Maior que."""
        self._filters.append(("gt", column, value))
        return self
    
    def gte(self, column: str, value):
        """Maior ou igual."""
        self._filters.append(("gte", column, value))
        return self
    
    def lt(self, column: str, value):
        """Menor que."""
        self._filters.append(("lt", column, value))
        return self
    
    def lte(self, column: str, value):
        """Menor ou igual."""
        self._filters.append(("lte", column, value))
        return self
    
    def like(self, column: str, pattern: str):
        """Busca com LIKE (% para wildcard)."""
        self._filters.append(("like", column, pattern))
        return self
    
    def ilike(self, column: str, pattern: str):
        """Busca com ILIKE (case insensitive)."""
        self._filters.append(("ilike", column, pattern))
        return self
    
    def is_null(self, column: str):
        """Verifica se é NULL."""
        self._filters.append(("is", column, "null"))
        return self
    
    def is_not_null(self, column: str):
        """Verifica se não é NULL."""
        self._filters.append(("not.is", column, "null"))
        return self
    
    def in_list(self, column: str, values: list):
        """Filtro IN (lista de valores)."""
        self._filters.append(("in", column, values))
        return self
    
    def order(self, column: str, desc: bool = False):
        """Ordena resultados."""
        self._order_column = column
        self._order_desc = desc
        return self
    
    def limit(self, count: int):
        """Limita quantidade de resultados."""
        self._limit_val = count
        return self
    
    def offset(self, count: int):
        """Pula N resultados."""
        self._offset_val = count
        return self
    
    def execute(self):
        """
        Executa a query e retorna os dados.
        
        Returns:
            Lista de dicionários com os resultados
        """
        try:
            query = supabase.table(self.table_name).select(self._columns)
            
            # Aplicar filtros
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    query = query.eq(column, value)
                elif filter_type == "neq":
                    query = query.neq(column, value)
                elif filter_type == "gt":
                    query = query.gt(column, value)
                elif filter_type == "gte":
                    query = query.gte(column, value)
                elif filter_type == "lt":
                    query = query.lt(column, value)
                elif filter_type == "lte":
                    query = query.lte(column, value)
                elif filter_type == "like":
                    query = query.like(column, value)
                elif filter_type == "ilike":
                    query = query.ilike(column, value)
                elif filter_type == "is":
                    query = query.is_(column, value)
                elif filter_type == "not.is":
                    query = query.not_.is_(column, value)
                elif filter_type == "in":
                    query = query.in_(column, value)
            
            # Ordenação
            if self._order_column:
                query = query.order(self._order_column, desc=self._order_desc)
            
            # Paginação
            if self._limit_val:
                query = query.limit(self._limit_val)
            if self._offset_val:
                query = query.offset(self._offset_val)
            
            result = query.execute()
            return result.data
        except Exception as e:
            print(f"[SUPABASE] Erro na query de {self.table_name}: {e}")
            return []
    
    def first(self):
        """Retorna apenas o primeiro resultado."""
        self._limit_val = 1
        results = self.execute()
        return results[0] if results else None
    
    def delete(self):
        """
        Deleta registros que correspondem aos filtros aplicados.
        IMPORTANTE: Deve ter pelo menos um filtro para evitar deleção acidental de todos os registros.
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            if not self._filters:
                print(f"[SUPABASE] AVISO: Tentativa de delete sem filtros em {self.table_name} - operação bloqueada")
                return False
            
            query = supabase.table(self.table_name).delete()
            
            # Aplicar filtros
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    query = query.eq(column, value)
                elif filter_type == "neq":
                    query = query.neq(column, value)
                elif filter_type == "gt":
                    query = query.gt(column, value)
                elif filter_type == "gte":
                    query = query.gte(column, value)
                elif filter_type == "lt":
                    query = query.lt(column, value)
                elif filter_type == "lte":
                    query = query.lte(column, value)
                elif filter_type == "in":
                    query = query.in_(column, value)
            
            query.execute()
            return True
        except Exception as e:
            print(f"[SUPABASE] Erro ao deletar de {self.table_name}: {e}")
            return False
    
    def count(self):
        """Retorna a contagem de resultados."""
        try:
            query = supabase.table(self.table_name).select("*", count="exact")
            
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    query = query.eq(column, value)
                elif filter_type == "neq":
                    query = query.neq(column, value)
                # ... outros filtros
            
            result = query.execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            print(f"[SUPABASE] Erro ao contar {self.table_name}: {e}")
            return 0
