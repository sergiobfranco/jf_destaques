# teste_fallback.py
# -*- coding: utf-8 -*-
import sys
import os

# Forçar UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, '.')

from encurtador_urls import GerenciadorURLs, encurtar_url_seguro
import time

def teste_fallback_manual():
    """
    Testa o fallback forçando falhas nos serviços
    """
    print("\n" + "="*80)
    print("TESTE DE FALLBACK - SIMULACAO DE FALHAS")
    print("="*80)
    
    url_teste = "https://www.google.com/search?q=teste"
    
    # Importar funções individuais
    from encurtador_urls import (
        encurtar_com_vgd,
        encurtar_com_clckru,
        encurtar_com_dagd,
        encurtar_com_ulvis,
        encurtar_com_isgd
    )
    
    servicos = [
        ("v.gd", encurtar_com_vgd),
        ("clck.ru", encurtar_com_clckru),
        ("da.gd", encurtar_com_dagd),
        ("ulvis.net", encurtar_com_ulvis),
        ("is.gd", encurtar_com_isgd),
    ]
    
    print("\n[1] TESTANDO CADA SERVICO INDIVIDUALMENTE:")
    print("-"*80)
    
    resultados = []
    
    for nome, funcao in servicos:
        print(f"\nTestando {nome}...", end=" ")
        try:
            inicio = time.time()
            resultado, info = funcao(url_teste)
            tempo = time.time() - inicio
            
            if resultado:
                print(f"OK ({tempo:.2f}s)")
                print(f"   URL: {resultado}")
                resultados.append((nome, "OK", resultado, tempo))
            else:
                print(f"FALHOU")
                print(f"   Motivo: {info}")
                resultados.append((nome, "FALHOU", None, tempo))
        except Exception as e:
            print(f"ERRO")
            print(f"   Excecao: {str(e)[:60]}")
            resultados.append((nome, "ERRO", None, 0))
        
        time.sleep(1)
    
    print("\n" + "="*80)
    print("RESUMO DOS TESTES INDIVIDUAIS:")
    print("="*80)
    
    for nome, status, url, tempo in resultados:
        emoji = "[OK]" if status == "OK" else "[X]"
        tempo_str = f"{tempo:.2f}s" if tempo > 0 else "-"
        print(f"{emoji} {nome:12} {status:8} {tempo_str:8} {url if url else ''}")
    
    # Contar quantos funcionam
    servicos_ok = sum(1 for _, s, _, _ in resultados if s == "OK")
    print(f"\nRESULTADO: {servicos_ok}/{len(servicos)} servicos funcionando")
    
    print("\n" + "="*80)
    print("[2] TESTANDO FALLBACK AUTOMATICO:")
    print("="*80)
    
    print("\nChamando encurtar_url_seguro() - deve usar fallback automatico:")
    print("-"*80)
    
    url_final = encurtar_url_seguro(url_teste, max_tentativas_por_servico=1, delay=0.5)
    
    print(f"\nRESULTADO FINAL: {url_final}")
    
    # Verificar qual serviço foi usado
    if url_final != url_teste:
        for nome, status, url, _ in resultados:
            if status == "OK" and nome.replace(".", "") in url_final.replace(".", ""):
                print(f"[OK] SERVICO USADO: {nome}")
                
                # Verificar se era o primeiro disponível
                primeiro_disponivel = next((n for n, s, _, _ in resultados if s == "OK"), None)
                if nome == primeiro_disponivel:
                    print(f"[OK] CORRETO: Usou o primeiro servico disponivel ({nome})")
                else:
                    print(f"[AVISO] Deveria usar {primeiro_disponivel}, mas usou {nome}")
                    print(f"[AVISO] POSSIVEL PROBLEMA NO FALLBACK!")
                break
    else:
        print(f"[AVISO] NENHUM SERVICO FUNCIONOU - URL original retornada")
    
    print("\n" + "="*80)
    print("[3] TESTANDO COM CACHE:")
    print("="*80)
    
    gerenciador = GerenciadorURLs('cache_teste_fallback.json')
    
    print("\nPrimeira chamada (sem cache):")
    url_cache_1 = gerenciador.obter_url_curta(url_teste)
    print(f"Resultado: {url_cache_1}")
    
    print("\nSegunda chamada (deve usar cache):")
    url_cache_2 = gerenciador.obter_url_curta(url_teste)
    print(f"Resultado: {url_cache_2}")
    
    if url_cache_1 == url_cache_2:
        print("[OK] Cache funcionando corretamente")
    else:
        print("[X] PROBLEMA: URLs diferentes entre chamadas!")
    
    gerenciador.estatisticas()
    
    print("\n" + "="*80)
    print("TESTE CONCLUIDO!")
    print("="*80)


if __name__ == "__main__":
    teste_fallback_manual()