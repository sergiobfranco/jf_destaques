import pandas as pd
import json
import sys

def analisar_noticias_estado(arquivo_csv):
    """
    Analisa as notícias do Estado de S.Paulo em busca de problemas
    """
    
    print("="*80)
    print("🔬 ANÁLISE DE NOTÍCIAS - IDENTIFICAÇÃO DE PROBLEMAS")
    print("="*80)
    
    # Carregar CSV
    print(f"\n📂 Carregando arquivo: {arquivo_csv}")
    df = pd.read_csv(arquivo_csv, encoding='utf-8')
    
    print(f"✅ Carregado: {len(df)} registros")
    print(f"\n📋 Colunas disponíveis:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")
    
    print(f"\n" + "="*80)
    print("🔍 ANÁLISE 1: CARACTERES PROBLEMÁTICOS")
    print("="*80)
    
    problemas_encontrados = []
    
    # Verificar cada linha
    for idx, row in df.iterrows():
        problemas_linha = []
        
        # Verificar cada campo de texto
        for col in df.columns:
            valor = row[col]
            
            if pd.isna(valor):
                continue
                
            valor_str = str(valor)
            
            # TESTE 1: Surrogates (causa o erro que você viu)
            try:
                valor_str.encode('utf-8')
            except UnicodeEncodeError as e:
                problemas_linha.append({
                    'tipo': 'SURROGATE',
                    'coluna': col,
                    'erro': str(e),
                    'valor': repr(valor_str)[:100]
                })
            
            # TESTE 2: Caracteres de controle
            caracteres_controle = [c for c in valor_str if ord(c) < 32 and c not in '\n\r\t']
            if caracteres_controle:
                problemas_linha.append({
                    'tipo': 'CARACTERE_CONTROLE',
                    'coluna': col,
                    'quantidade': len(caracteres_controle),
                    'valor': repr(valor_str)[:100]
                })
            
            # TESTE 3: Emojis problemáticos
            try:
                # Tentar detectar surrogates não-pares
                if '\\ud' in repr(valor_str):
                    problemas_linha.append({
                        'tipo': 'EMOJI_MAL_FORMADO',
                        'coluna': col,
                        'valor': repr(valor_str)[:100]
                    })
            except:
                pass
            
            # TESTE 4: Comprimento suspeito
            if len(valor_str) > 50000:  # Muito longo
                problemas_linha.append({
                    'tipo': 'TEXTO_MUITO_LONGO',
                    'coluna': col,
                    'tamanho': len(valor_str)
                })
        
        if problemas_linha:
            problemas_encontrados.append({
                'linha': idx,
                'id': row.get('Id', row.get('ID', 'N/A')),
                'titulo': str(row.get('Titulo', row.get('Título', 'N/A')))[:70],
                'problemas': problemas_linha
            })
    
    # Exibir resultados
    if problemas_encontrados:
        print(f"\n🔴 ENCONTRADOS {len(problemas_encontrados)} REGISTROS COM PROBLEMAS:\n")
        
        for item in problemas_encontrados:
            print(f"\n{'─'*80}")
            print(f"📰 LINHA {item['linha']} | ID: {item['id']}")
            print(f"   Título: {item['titulo']}...")
            print(f"\n   ⚠️ PROBLEMAS ENCONTRADOS:")
            
            for prob in item['problemas']:
                print(f"\n      🔸 Tipo: {prob['tipo']}")
                print(f"         Coluna: {prob['coluna']}")
                if 'erro' in prob:
                    print(f"         Erro: {prob['erro']}")
                if 'valor' in prob:
                    print(f"         Valor: {prob['valor']}")
                if 'tamanho' in prob:
                    print(f"         Tamanho: {prob['tamanho']} caracteres")
    else:
        print("\n✅ NENHUM PROBLEMA DE ENCODING ENCONTRADO!")
    
    print(f"\n" + "="*80)
    print("🔍 ANÁLISE 2: ESTATÍSTICAS GERAIS")
    print("="*80)
    
    # Verificar campos com valores NULL
    print(f"\n📊 Campos com valores NULL:")
    nulls = df.isnull().sum()
    for col in df.columns:
        if nulls[col] > 0:
            print(f"   {col}: {nulls[col]} ({nulls[col]/len(df)*100:.1f}%)")
    
    # Verificar tamanhos de campos
    print(f"\n📏 Tamanho médio dos campos de texto:")
    for col in df.columns:
        if df[col].dtype == 'object':
            tamanhos = df[col].astype(str).str.len()
            print(f"   {col}:")
            print(f"      Média: {tamanhos.mean():.0f} chars")
            print(f"      Máximo: {tamanhos.max():.0f} chars")
            print(f"      Registro com maior tamanho: linha {tamanhos.idxmax()}")
    
    print(f"\n" + "="*80)
    print("🔍 ANÁLISE 3: TENTATIVA DE SERIALIZAÇÃO JSON")
    print("="*80)
    
    # Tentar converter cada linha para JSON (simula o que a API faz)
    linhas_falham_json = []
    
    for idx, row in df.iterrows():
        try:
            # Converter para dict
            row_dict = row.to_dict()
            
            # Tentar serializar para JSON
            json_str = json.dumps(row_dict, ensure_ascii=False)
            
            # Tentar encodar em UTF-8
            json_str.encode('utf-8')
            
        except Exception as e:
            linhas_falham_json.append({
                'linha': idx,
                'id': row.get('Id', row.get('ID', 'N/A')),
                'titulo': str(row.get('Titulo', row.get('Título', 'N/A')))[:70],
                'erro': str(e)
            })
    
    if linhas_falham_json:
        print(f"\n🔴 {len(linhas_falham_json)} LINHAS FALHAM NA SERIALIZAÇÃO JSON:\n")
        
        for item in linhas_falham_json:
            print(f"\n   📰 LINHA {item['linha']} | ID: {item['id']}")
            print(f"      Título: {item['titulo']}...")
            print(f"      ❌ Erro: {item['erro']}")
    else:
        print("\n✅ TODAS AS LINHAS PODEM SER SERIALIZADAS EM JSON!")
    
    print(f"\n" + "="*80)
    print("📊 RESUMO FINAL")
    print("="*80)
    print(f"\nTotal de registros analisados: {len(df)}")
    print(f"Registros com problemas de encoding: {len(problemas_encontrados)}")
    print(f"Registros que falham em JSON: {len(linhas_falham_json)}")
    
    if problemas_encontrados or linhas_falham_json:
        print(f"\n🎯 AÇÃO RECOMENDADA:")
        print(f"   Os IDs problemáticos devem ser reportados ao suporte da BoxNet")
        print(f"   ou excluídos temporariamente do processamento.")
        
        # Salvar IDs problemáticos
        ids_problema = set()
        for item in problemas_encontrados:
            ids_problema.add(item['id'])
        for item in linhas_falham_json:
            ids_problema.add(item['id'])
        
        print(f"\n📋 IDs problemáticos ({len(ids_problema)}):")
        for id_prob in sorted(ids_problema):
            print(f"   - {id_prob}")
    
    print("="*80)
    
    return problemas_encontrados, linhas_falham_json


# EXECUTAR
if __name__ == "__main__":
    arquivo = "Relatorio-13-03-2026-17-27-53-911.csv"
    
    problemas, falhas_json = analisar_noticias_estado(arquivo)
    
    print(f"\n✅ Análise concluída!")
    
    if problemas or falhas_json:
        print(f"\n💡 Próximos passos:")
        print(f"   1. Reportar IDs problemáticos ao suporte da BoxNet")
        print(f"   2. Solicitar correção dos dados na fonte")
        print(f"   3. Implementar filtro temporário para excluir esses IDs")