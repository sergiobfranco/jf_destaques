# verificar_cache.py
# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import json
import os
from datetime import datetime

arquivo_cache = 'dados/cache_urls.json'

print("="*80)
print("VERIFICACAO DO CACHE DE URLs")
print("="*80)

if os.path.exists(arquivo_cache):
    with open(arquivo_cache, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    print(f"\n[INFO] Cache tem {len(cache)} URLs")
    print(f"[INFO] Arquivo: {arquivo_cache}")
    print(f"[INFO] Tamanho: {os.path.getsize(arquivo_cache)} bytes")
    
    # Contar por serviço
    servicos_usados = {}
    for url_original, dados in cache.items():
        servico = dados.get('servico', 'desconhecido')
        servicos_usados[servico] = servicos_usados.get(servico, 0) + 1
    
    print("\n" + "-"*80)
    print("DISTRIBUICAO POR SERVICO:")
    print("-"*80)
    for servico, count in sorted(servicos_usados.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(cache) * 100
        print(f"   {servico:15} -> {count:4} URLs ({pct:5.1f}%)")
    
    # Verificar últimas URLs adicionadas (podem ser da madrugada)
    print("\n" + "-"*80)
    print("ULTIMAS 20 URLs ADICIONADAS AO CACHE:")
    print("-"*80)
    
    urls_ordenadas = sorted(
        cache.items(), 
        key=lambda x: x[1].get('data', ''), 
        reverse=True
    )
    
    for i, (url_orig, dados) in enumerate(urls_ordenadas[:20], 1):
        data_str = dados.get('data', 'N/A')
        servico = dados.get('servico', 'N/A')
        url_curta = dados.get('url_curta', 'N/A')
        
        # Formatar data
        try:
            if data_str != 'N/A':
                dt = datetime.fromisoformat(data_str)
                data_formatada = dt.strftime("%d/%m/%Y %H:%M:%S")
            else:
                data_formatada = 'N/A'
        except:
            data_formatada = data_str
        
        print(f"\n[{i:2}] Data: {data_formatada}")
        print(f"    Servico: {servico}")
        print(f"    URL original: {url_orig[:60]}...")
        print(f"    URL curta: {url_curta}")
    
    # Análise específica: procurar is.gd recentes
    print("\n" + "-"*80)
    print("ANALISE: URLs ENCURTADAS COM IS.GD (ultimas 24h):")
    print("-"*80)
    
    from datetime import timedelta
    agora = datetime.now()
    urls_isgd_recentes = []
    
    for url_orig, dados in cache.items():
        if dados.get('servico') == 'is.gd':
            data_str = dados.get('data', '')
            try:
                dt = datetime.fromisoformat(data_str)
                if (agora - dt) < timedelta(hours=24):
                    urls_isgd_recentes.append((dt, dados))
            except:
                pass
    
    if urls_isgd_recentes:
        print(f"\n[ATENCAO] Encontradas {len(urls_isgd_recentes)} URLs usando is.gd nas ultimas 24h:")
        urls_isgd_recentes.sort(key=lambda x: x[0], reverse=True)
        
        for dt, dados in urls_isgd_recentes[:10]:
            print(f"\n   Data: {dt.strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"   URL: {dados.get('url_curta')}")
    else:
        print("\n[OK] Nenhuma URL usando is.gd nas ultimas 24h")
    
    # Verificar primeiro serviço usado (deve ser v.gd)
    print("\n" + "-"*80)
    print("VERIFICACAO: Qual servico esta sendo usado PRIMEIRO?")
    print("-"*80)
    
    if servicos_usados:
        servico_mais_usado = max(servicos_usados.items(), key=lambda x: x[1])[0]
        print(f"\n[INFO] Servico mais usado no cache: {servico_mais_usado}")
        
        if servico_mais_usado == 'v.gd':
            print("[OK] Correto! v.gd deve ser o mais usado (primeiro na ordem)")
        elif servico_mais_usado == 'is.gd':
            print("[AVISO] is.gd e o mais usado - pode indicar problema!")
            print("[AVISO] is.gd deveria ser o ULTIMO recurso, nao o primeiro")
        else:
            print(f"[INFO] {servico_mais_usado} esta sendo mais usado")
    
else:
    print("\n[ERRO] Arquivo de cache nao encontrado")
    print(f"[ERRO] Procurado em: {arquivo_cache}")

print("\n" + "="*80)
print("VERIFICACAO CONCLUIDA!")
print("="*80)