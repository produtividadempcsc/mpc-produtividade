
import os
import sys
from datetime import datetime
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import select_all, update_by_id, QueryBuilder

def backfill_finalizacao():
    print("Starting backfill of data_finalizacao...")
    
    # 1. Get all completed processes that are missing data_finalizacao
    # (Checking status_chefe='Finalizado' and/or status_servidor='Finalizado')
    processes = QueryBuilder("processos")\
        .eq("status_chefe", "Finalizado")\
        .execute()
    
    print(f"Found {len(processes)} finalized processes.")
    
    updated_count = 0
    
    for p in processes:
        if p.get('data_finalizacao'):
            continue  # Already has date
            
        pid = p['id']
        
        # 2. Query history to find when it was finalized
        # Look for history entries for this process
        history = QueryBuilder("processo_historico")\
            .eq("id_processo", pid)\
            .order("timestamp", desc=True)\
            .execute()
        
        finalization_date = None
        
        # Naive strategy: The most recent history entry for a finalized process MIGHT be the finalization.
        # Or look for specific text in description if available?
        # Since I can't see the description history, I will assume the timestamp of the LAST history entry
        # is a good approximation for when it was last touched (finalized).
        # Better: Look for transition to 'Finalizado' if tracked.
        
        # If history exists, use the latest timestamp
        if history:
            finalization_date = history[0]['timestamp']
        else:
            # If no history, fallback to data_conclusao_chefe (better than nothing, but technically wrong if procurator delayed)
            # OR leave as is?
            # User wants report accuracy.
            # If I use data_conclusao_chefe, then Metric 8 (Acervo Procurador) will be 0 duration.
            # Maybe use today? No.
            # Use data_conclusao_chefe + 1 day?
            # Let's use data_criacao_registro as a fallback if it was created as finalized? No.
             print(f"Process {pid} has no history. Skipping.")
             continue

        if finalization_date:
            print(f"Updating process {pid} with finalization date: {finalization_date}")
            update_by_id("processos", pid, {"data_finalizacao": finalization_date})
            updated_count += 1
            
    print(f"Backfill complete. Updated {updated_count} processes.")

if __name__ == "__main__":
    backfill_finalizacao()
