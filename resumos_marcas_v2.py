# Etapa 2: Resumo de até 60 palavras, agrupamento semântico e geração de resumos finais com refinamento por subtemas
# Versão 5: Adicionado tratamento de datas - Remove datas passadas, mantém datas futuras
# Data: 03/02/2026

import pandas as pd
import os
import requests
import re
import configparser
import traceback
import datetime
import time
import random
from dotenv import load_dotenv

def obter_chave_deepseek():
    load_dotenv()
    config_path = os.path.join("dados", "config", "config_usuario.ini")
    print(f"🛠️ Lendo config de: {config_path}")
    
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    perfil = config.get("usuario", "perfil", fallback="client").strip().lower()
    
    env_var = f"DEEPSEEK_API_KEY_{perfil.upper()}"
    chave = os.getenv(env_var)
    
    print(f"Perfil de usuário: {perfil}")
    print(f"Variável de ambiente esperada: {env_var}")
    print(f"Chave encontrada: {chave[:10]}..." if chave else "❌ Nenhuma chave encontrada")
    
    if not chave:
        raise ValueError(f"Chave de API não encontrada para o perfil '{perfil}' ({env_var}) no arquivo .env")
    
    return chave


from config import DEEPSEEK_API_URL, w_marcas


def carregar_verbos_iniciais():
    """
    Carrega os verbos do arquivo DOCX e separa em singular e plural.
    Retorna dois dicionários: verbos_singular e verbos_plural
    """
    try:
        from docx import Document
        
        caminho_docx = os.path.join("dados", "config", "VERBOS_PARA_INICIAR_RESUMOS.docx")
        
        # Fallback: tentar na raiz do projeto
        if not os.path.exists(caminho_docx):
            caminho_docx = "VERBOS_PARA_INICIAR_RESUMOS.docx"
        
        if not os.path.exists(caminho_docx):
            print("⚠️ Arquivo VERBOS_PARA_INICIAR_RESUMOS.docx não encontrado. Usando verbos padrão.")
            return obter_verbos_padrao()
        
        doc = Document(caminho_docx)
        verbos_singular = []
        verbos_plural = []
        
        for para in doc.paragraphs:
            texto = para.text.strip()
            if not texto:
                continue
            
            # Identificar se é singular ou plural baseado na terminação
            # Plural termina com: 'am que', 'em que', 'ão que'
            # Exemplos: divulgam que, trazem que, trazem divulgação que
            if any(texto.endswith(sufixo) for sufixo in ['am que', 'em que', 'ão que']):
                verbos_plural.append(texto)
            else:
                verbos_singular.append(texto)
        
        print(f"✅ Carregados {len(verbos_singular)} verbos no singular e {len(verbos_plural)} no plural")
        return verbos_singular, verbos_plural
        
    except ImportError:
        print("⚠️ Biblioteca python-docx não instalada. Usando verbos padrão.")
        return obter_verbos_padrao()
    except Exception as e:
        print(f"⚠️ Erro ao carregar DOCX: {e}. Usando verbos padrão.")
        return obter_verbos_padrao()


def pos_processar_validacao_verbos(df_final, verbos_singular, verbos_plural):
    """
    Pós-processamento: Valida e corrige inconsistências entre QtdNoticias e verbos usados.
    
    Esta função:
    1. Reconta IDs reais no campo 'Ids'
    2. Detecta o verbo usado no resumo
    3. Corrige automaticamente se houver inconsistência
    
    Args:
        df_final: DataFrame com os resumos gerados
        verbos_singular: lista de verbos no singular
        verbos_plural: lista de verbos no plural
    
    Returns:
        DataFrame corrigido
    """
    print("\n🔍 === PÓS-PROCESSAMENTO: VALIDAÇÃO DE VERBOS ===")
    
    if df_final.empty:
        print("⚠️ DataFrame vazio, nada a processar")
        return df_final
    
    df = df_final.copy()
    correcoes_realizadas = 0
    
    # Criar mapeamento de verbos para facilitar substituição (pareamento por índice)
    mapa_singular_plural = {}
    mapa_plural_singular = {}
    
    # Usar pareamento por índice (já que agora vem do Excel com correspondência garantida)
    for i in range(min(len(verbos_singular), len(verbos_plural))):
        sing = verbos_singular[i]
        plur = verbos_plural[i]
        mapa_singular_plural[sing] = plur
        mapa_plural_singular[plur] = sing
    
    print(f"📋 Mapeamento criado: {len(mapa_singular_plural)} pares de verbos")
    
    for idx, row in df.iterrows():
        ids_str = str(row.get('Ids', ''))
        resumo = str(row.get('Resumo', ''))
        qtd_declarada = row.get('QtdNoticias', 0)
        
        # 1. Contar IDs reais
        ids_array = [id.strip() for id in ids_str.split(',') if id.strip()]
        qtd_real = len(ids_array)
        
        # 2. Detectar verbo usado
        verbo_usado = None
        tipo_verbo_usado = None
        
        for verbo_sing in verbos_singular:
            if resumo.startswith(verbo_sing + " "):
                verbo_usado = verbo_sing
                tipo_verbo_usado = 'singular'
                break
        
        if not verbo_usado:
            for verbo_plur in verbos_plural:
                if resumo.startswith(verbo_plur + " "):
                    verbo_usado = verbo_plur
                    tipo_verbo_usado = 'plural'
                    break
        
        if not verbo_usado:
            print(f"⚠️ Linha {idx}: Verbo não detectado no resumo")
            print(f"   Início do resumo: '{resumo[:50]}...'")
            continue
        
        # 3. Verificar inconsistência
        tipo_correto = 'singular' if qtd_real == 1 else 'plural'
        
        if tipo_verbo_usado != tipo_correto:
            print(f"🔧 Linha {idx}: Corrigindo inconsistência")
            print(f"   IDs: {ids_str[:50]}{'...' if len(ids_str) > 50 else ''}")
            print(f"   QtdReal: {qtd_real} | QtdDeclarada: {qtd_declarada}")
            print(f"   Verbo usado: '{verbo_usado}' ({tipo_verbo_usado})")
            print(f"   Deveria ser: {tipo_correto}")
            
            # 4. Substituir verbo usando o mapeamento do Excel
            if tipo_correto == 'singular' and verbo_usado in mapa_plural_singular:
                verbo_correto = mapa_plural_singular[verbo_usado]
                resumo_corrigido = resumo.replace(verbo_usado + " ", verbo_correto + " ", 1)
                df.at[idx, 'Resumo'] = resumo_corrigido
                print(f"   ✅ Substituído: '{verbo_usado}' → '{verbo_correto}'")
                correcoes_realizadas += 1
                
            elif tipo_correto == 'plural' and verbo_usado in mapa_singular_plural:
                verbo_correto = mapa_singular_plural[verbo_usado]
                resumo_corrigido = resumo.replace(verbo_usado + " ", verbo_correto + " ", 1)
                df.at[idx, 'Resumo'] = resumo_corrigido
                print(f"   ✅ Substituído: '{verbo_usado}' → '{verbo_correto}'")
                correcoes_realizadas += 1
            else:
                print(f"   ❌ Mapeamento não encontrado para '{verbo_usado}'")
    
    if correcoes_realizadas > 0:
        print(f"\n✅ Pós-processamento concluído: {correcoes_realizadas} correções realizadas")
    else:
        print(f"\n✅ Pós-processamento concluído: Nenhuma correção necessária")
    
    return df


def obter_verbos_padrao():
    """Retorna listas de verbos padrão para singular e plural"""
    verbos_singular = [
        "repercute que",
        "aponta que",
        "destaca que",
        "divulga que",
        "informa que",
        "traz divulgação que",
        "traz conteúdo que",
        "publica que",
        "comunica que",
        "mostra que"
    ]
    
    verbos_plural = [
        "repercutem que",
        "apontam que",
        "destacam que",
        "divulgam que",
        "informam que",
        "trazem divulgação que",
        "trazem conteúdo que",
        "publicam que",
        "comunicam que",
        "mostram que"
    ]
    
    return verbos_singular, verbos_plural


def adicionar_prefixo_resumo(resumo, qtd_noticias, verbos_singular, verbos_plural, pool_verbos):
    """
    Adiciona prefixo ao resumo baseado na quantidade de notícias.
    Usa distribuição balanceada de verbos (Opção A).
    
    Args:
        resumo: texto do resumo
        qtd_noticias: quantidade de notícias agrupadas
        verbos_singular: lista de expressões no singular
        verbos_plural: lista de expressões no plural
        pool_verbos: dicionário com pools embaralhados {'singular': [...], 'plural': [...]}
    
    Returns:
        resumo com prefixo adequado
    """
    if not resumo or resumo.strip() == "":
        return resumo
    
    # Escolher lista apropriada (singular ou plural) BASEADO APENAS EM qtd_noticias
    if qtd_noticias == 1:
        lista_tipo = 'singular'
        lista_verbos_original = verbos_singular
    else:
        lista_tipo = 'plural'
        lista_verbos_original = verbos_plural
    
    # Debug adicional
    print(f"    🔹 adicionar_prefixo_resumo chamado: qtd={qtd_noticias}, tipo='{lista_tipo}'")
    
    # Se o pool estiver vazio, reabastece com lista embaralhada
    if not pool_verbos[lista_tipo]:
        pool_verbos[lista_tipo] = lista_verbos_original.copy()
        random.shuffle(pool_verbos[lista_tipo])
        print(f"    🔄 Pool '{lista_tipo}' reabastecido: {len(pool_verbos[lista_tipo])} verbos")
    
    # Pega o próximo verbo do pool (sem repetição até esgotar)
    verbo = pool_verbos[lista_tipo].pop(0)
    print(f"    ✓ Verbo selecionado: '{verbo}' (pool restante: {len(pool_verbos[lista_tipo])})")
    
    # Garantir que o resumo está limpo (sem \n no início/fim) e começa com minúscula
    resumo_limpo = resumo.strip()
    resumo_ajustado = resumo_limpo[0].lower() + resumo_limpo[1:] if len(resumo_limpo) > 1 else resumo_limpo.lower()
    
    # Montar o resumo final (todos os verbos agora terminam com "que")
    resumo_final = f"{verbo} {resumo_ajustado}"
    
    return resumo_final


def limpar_frases_introdutorias(texto_resumo):
    """Remove frases introdutórias comuns que o LLM pode adicionar"""
    if not texto_resumo:
        return texto_resumo
    
    # Padrões de frases introdutórias a remover (case-insensitive)
    padroes_remover = [
        r'^aqui está um resumo.*?:\s*',
        r'^aqui está o resumo.*?:\s*',
        r'^segue um resumo.*?:\s*',
        r'^baseado no texto fornecido,?\s*o resumo.*?:\s*',
        r'^baseado no texto fornecido,?\s*',
        r'^o resumo para a marca.*?:\s*',
        r'^o resumo é:?\s*',
        r'^resumo:?\s*',
        r'^segue:?\s*',
    ]
    
    texto_limpo = texto_resumo.strip()
    for padrao in padroes_remover:
        texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE)
    
    return texto_limpo.strip()


def remover_datas_passadas(texto_resumo):
    """
    Nova função: Remove menções explícitas a datas que se referem a eventos no passado.
    Mantém datas futuras (com verbos no futuro ou expressões como "previsto para", "deve ocorrer em").
    
    Esta função identifica padrões de datas associadas a verbos no passado e as remove,
    mantendo apenas datas associadas a eventos futuros.
    
    Exemplos:
    - Remove: "anunciou em 29/01/2026", "afirmou em 29 de janeiro", "em 29 de janeiro, a empresa lançou"
    - Mantém: "previsto para 10 de fevereiro", "deve ocorrer em 11 de fevereiro"
    
    Args:
        texto_resumo: texto do resumo a ser processado
        
    Returns:
        texto sem datas passadas
    """
    if not texto_resumo:
        return texto_resumo
    
    print(f"\n🔍 [REMOVER_DATAS_PASSADAS] Texto original: {texto_resumo[:100]}...")
    
    # ========== PADRÃO 1: Datas com formato DD/MM/YYYY ==========
    # Remove: "em 29/01/2026", "dia 29/01/2026", "na data 29/01/2026"
    # Padrão: palavra + "em" ou "dia" + data DD/MM/YYYY
    padrao_data_barra = r'\b(em|dia|na data|no dia)\s+\d{1,2}/\d{1,2}/\d{4}\b'
    texto_modificado = re.sub(padrao_data_barra, '', texto_resumo, flags=re.IGNORECASE)
    
    # ========== PADRÃO 2: Datas com formato "DD de MÊS" ou "DD de MÊS de YYYY" ==========
    # Remove: "em 29 de janeiro", "dia 29 de janeiro de 2026", "na quinta-feira (29)"
    meses = r'(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
    
    # Padrão 2a: "em DD de MÊS" (remove se NÃO precedido por verbos futuros)
    # Primeiro, proteger datas futuras marcando-as temporariamente
    texto_modificado = re.sub(
        r'\b(previsto para|prevista para|programado para|deve ocorrer em|ocorrerá em|acontecerá em|será em|será no dia|marcado para|agendado para)\s+(\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?)',
        r'__PROTEGER_DATA__\1 \2__FIM_PROTECAO__',
        texto_modificado,
        flags=re.IGNORECASE
    )
    
    # Padrão 2b: Remover datas após verbos no passado (ex: "anunciou 2 de dezembro", "informou em 29 de janeiro")
    # Lista de verbos comuns no passado
    verbos_passado = r'(?:anunciou|informou|divulgou|publicou|comunicou|reportou|declarou|afirmou|revelou|confirmou|lançou|apresentou|mostrou|indicou)'
    padrao_verbo_data = r'\b(' + verbos_passado + r')\s+(?:em\s+)?\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b'
    texto_modificado = re.sub(padrao_verbo_data, r'\1', texto_modificado, flags=re.IGNORECASE)
    
    # Padrão 2c: Remover datas com preposições explícitas (padrão original)
    padrao_data_extenso = r'\b(?:em|dia|no dia|na data|nesta|nesta data|neste dia)\s+\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b'
    texto_modificado = re.sub(padrao_data_extenso, '', texto_modificado, flags=re.IGNORECASE)
    
    # ========== PADRÃO 3: Datas com dia da semana e número ==========
    # Remove: "nesta quinta-feira (29)", "na última quinta-feira (29)"
    dias_semana = r'(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:-feira)?'
    padrao_dia_semana = r'\b(?:nesta|neste|na|no|desta|deste|da|do|última|último)\s+' + dias_semana + r'\s*\(\d{1,2}\)'
    texto_modificado = re.sub(padrao_dia_semana, '', texto_modificado, flags=re.IGNORECASE)
    
    # ========== PADRÃO 4: Limpeza de resíduos ==========
    # Remove espaços duplos, vírgulas órfãs e outros resíduos
    texto_modificado = re.sub(r'^\s*,\s*', '', texto_modificado)  # Remove vírgula no início
    texto_modificado = re.sub(r'\s+,', ',', texto_modificado)  # Remove espaços antes de vírgulas
    texto_modificado = re.sub(r',\s*,', ',', texto_modificado)  # Remove vírgulas duplas
    texto_modificado = re.sub(r'\s{2,}', ' ', texto_modificado)  # Remove espaços múltiplos
    texto_modificado = re.sub(r'\b(na|no|da|do)\s+(na|no|da|do|após|antes)\b', r'\2', texto_modificado, flags=re.IGNORECASE)  # Remove preposições duplicadas
    
    # ========== RESTAURAR DATAS PROTEGIDAS ==========
    texto_modificado = re.sub(r'__PROTEGER_DATA__', '', texto_modificado)
    texto_modificado = re.sub(r'__FIM_PROTECAO__', '', texto_modificado)
    
    # Limpar espaços no início e fim
    texto_final = texto_modificado.strip()
    
    # Log das alterações
    if texto_final != texto_resumo:
        print(f"✅ [REMOVER_DATAS_PASSADAS] Datas passadas removidas")
        print(f"   Original: {texto_resumo[:100]}...")
        print(f"   Modificado: {texto_final[:100]}...")
    else:
        print(f"ℹ️  [REMOVER_DATAS_PASSADAS] Nenhuma data passada encontrada para remover")
    
    return texto_final


def corrigir_datas_inventadas(texto_resumo, texto_original):
    """
    O DeepSeek às vezes ignora a instrução e expande "sexta-feira (23)" 
    para "sexta-feira, 23 de agosto" ou até remove a menção ao dia da semana
    deixando apenas "em 23 de agosto".
    
    Também expande "amanhã, 28" para "28 de fevereiro" (inventando mês).
    
    Esta função:
    1. Procura no texto ORIGINAL por padrões "dia_da_semana (DD)" e "amanhã, DD"
    2. Usa essa informação para corrigir o resumo
    3. Converte datas inventadas de volta para o formato correto
    
    Padrões convertidos:
    - "sexta-feira, 23 de agosto" → "nesta sexta-feira (23)"
    - "em 23 de agosto" + original tem "sexta-feira (23)" → "nesta sexta-feira (23)"
    - "28 de fevereiro" + original tem "amanhã, 28" → "amanhã (28)"
    """
    if not texto_resumo:
        return texto_resumo
    
    dias_semana = [
        'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo',
        'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado-feira', 'domingo-feira'
    ]
    meses = [
        'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ]
    
    # ════════════════════════════════════════════════════════════
    # ESTRATÉGIA 0: Procurar por "amanhã, DD" no texto original
    # ════════════════════════════════════════════════════════════
    pattern_amanha = r'\bamanhã\s*,?\s*(\d{1,2})\b'
    match_amanha = re.search(pattern_amanha, texto_original, re.IGNORECASE)
    
    if match_amanha:
        numero_amanha = match_amanha.group(1)
        print(f"🔍 DEBUG corrigir_datas: Encontrado 'amanhã, {numero_amanha}'")
        
        # Procurar no resumo por "DD de [mês]" e substituir por "amanhã (DD)"
        pattern_data_inventada = r'\b' + numero_amanha + r'\s+de\s+(?:' + '|'.join(meses) + r')\b'
        match_data = re.search(pattern_data_inventada, texto_resumo, re.IGNORECASE)
        
        if match_data:
            print(f"   ✓ Encontrado padrão de data inventada: '{match_data.group(0)}'")
            # Substituir "DD de [mês]" por "amanhã (DD)"
            texto_resumo = re.sub(pattern_data_inventada, f'amanhã ({numero_amanha})', texto_resumo, flags=re.IGNORECASE)
            print(f"   → Corrigido para: 'amanhã ({numero_amanha})'")
            return texto_resumo
        else:
            print(f"   ✗ Padrão de data inventada NÃO encontrado para {numero_amanha}")
    
    # ════════════════════════════════════════════════════════════
    # ESTRATÉGIA 1: Procurar no texto original por "dia_da_semana (DD)"
    # ════════════════════════════════════════════════════════════
    # Padrão: "(nesta|desta|na) sexta-feira (23)"
    pattern_original = r'\b(?:nesta|desta|na|no)\s+(' + '|'.join(dias_semana) + r')\s*(?:-feira)?\s*\((\d{1,2})\)'
    match_original = re.search(pattern_original, texto_original, re.IGNORECASE)
    
    # DEBUG: Printar se encontrou ou não
    print(f"🔍 DEBUG corrigir_datas: pattern_original encontrado? {match_original is not None}")
    if match_original:
        print(f"   → Match: '{match_original.group(0)}'")
        print(f"   → Grupo 1 (dia): '{match_original.group(1)}'")
        print(f"   → Grupo 2 (num): '{match_original.group(2)}'")
    else:
        print(f"   → Nenhum match encontrado no texto original")
        print(f"   → Primeiros 200 chars do original: {texto_original[:200]}")
    
    if match_original:
        dia_semana_original = match_original.group(1)
        numero_original = match_original.group(2)
        
        # Garantir que tem "-feira" se não tiver
        if 'segunda' in dia_semana_original.lower() and '-feira' not in dia_semana_original:
            dia_semana_original = 'segunda-feira'
        elif 'terça' in dia_semana_original.lower() and '-feira' not in dia_semana_original:
            dia_semana_original = 'terça-feira'
        elif 'quarta' in dia_semana_original.lower() and '-feira' not in dia_semana_original:
            dia_semana_original = 'quarta-feira'
        elif 'quinta' in dia_semana_original.lower() and '-feira' not in dia_semana_original:
            dia_semana_original = 'quinta-feira'
        elif 'sexta' in dia_semana_original.lower() and '-feira' not in dia_semana_original:
            dia_semana_original = 'sexta-feira'
        
        print(f"   → Dia normalizado: '{dia_semana_original}', número: {numero_original}")
        
        # Procurar por qualquer padrão de data no resumo que mencione esse número
        # e substituir por "nesta [dia] ([número])"
        
        # Padrão 1: "dia_da_semana, DD de [mês]"
        pattern1 = r'\b(' + '|'.join(dias_semana) + r')\s*(?:-feira)?\s*,?\s*' + numero_original + r'\s+de\s+(?:' + '|'.join(meses) + r')\b'
        match1 = re.search(pattern1, texto_resumo, re.IGNORECASE)
        if match1:
            print(f"   ✓ Pattern 1 encontrado: '{match1.group(0)}'")
            texto_resumo = re.sub(pattern1, f'nesta {dia_semana_original} ({numero_original})', texto_resumo, flags=re.IGNORECASE)
        else:
            print(f"   ✗ Pattern 1 NÃO encontrado")
        
        # Padrão 2: "em DD de [mês]" (sem dia da semana)
        pattern2 = r'\bem\s+' + numero_original + r'\s+de\s+(?:' + '|'.join(meses) + r')\b'
        match2 = re.search(pattern2, texto_resumo, re.IGNORECASE)
        if match2:
            print(f"   ✓ Pattern 2 encontrado: '{match2.group(0)}'")
            texto_resumo = re.sub(pattern2, f'nesta {dia_semana_original} ({numero_original})', texto_resumo, flags=re.IGNORECASE)
        else:
            print(f"   ✗ Pattern 2 NÃO encontrado")
        
        # Padrão 3: Apenas "DD de [mês]" (sem preposição)
        pattern3 = r'\b' + numero_original + r'\s+de\s+(?:' + '|'.join(meses) + r')(?:\s+de\s+\d{4})?\b'
        match3 = re.search(pattern3, texto_resumo, re.IGNORECASE)
        if match3:
            print(f"   ✓ Pattern 3 encontrado: '{match3.group(0)}'")
            texto_resumo = re.sub(pattern3, f'nesta {dia_semana_original} ({numero_original})', texto_resumo, flags=re.IGNORECASE)
        else:
            print(f"   ✗ Pattern 3 NÃO encontrado")
    
    return texto_resumo


def processar_marcas_v2(arq_textos):
    """
    Processa textos de notícias e gera resumos consolidados por marca.
    
    Versão 2 com melhorias:
    - Agrupamento semântico mais inteligente
    - Seleção balanceada de verbos iniciais
    - Tratamento de datas: remove datas passadas, mantém datas futuras
    """
    import json
    
    # ========== Configuração da API DeepSeek ==========
    api_key = obter_chave_deepseek()
    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    LIMITE_CARACTERES_GRUPO = 12000  # Limite seguro para evitar overflow
    
    # Carregar verbos do DOCX ou usar padrão
    verbos_singular, verbos_plural = carregar_verbos_iniciais()
    
    # ========== NOVO: Pool de verbos para distribuição balanceada ==========
    # Embaralhar uma vez no início, e ir consumindo
    pool_verbos = {
        'singular': verbos_singular.copy(),
        'plural': verbos_plural.copy()
    }
    random.shuffle(pool_verbos['singular'])
    random.shuffle(pool_verbos['plural'])
    print(f"🎲 Pools de verbos inicializados: {len(pool_verbos['singular'])} singular, {len(pool_verbos['plural'])} plural")
    # =====================================================================
    
    def _normalize_df(arq):
        """Normaliza dataframe de entrada"""
        if isinstance(arq, str):
            df = pd.read_excel(arq) if arq.endswith(('.xlsx', '.xls')) else pd.read_csv(arq)
        else:
            df = arq.copy()
        
        # Normalizar nomes de colunas
        df.columns = df.columns.str.strip()
        
        # Mapeamento de colunas possíveis
        col_map = {
            'Título': 'Titulo',
            'titulo': 'Titulo',
            'Conteúdo': 'Conteudo',
            'conteudo': 'Conteudo',
            'Conteúdo da Notícia': 'Conteudo',
            'Canal': 'Canais',
            'canais': 'Canais',
            'URL de Visualização': 'UrlVisualizacao',
            'url_visualizacao': 'UrlVisualizacao'
        }
        
        for old_name, new_name in col_map.items():
            if old_name in df.columns:
                df.rename(columns={old_name: new_name}, inplace=True)
        
        # Validar colunas obrigatórias
        required = ['Id', 'Titulo', 'Conteudo', 'Canais']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
        
        return df

    def gerar_resumo_60(texto, id_noticia):
        """Gera resumo de até 60 palavras preservando o tempo verbal original"""
        prompt = f"""Gere um resumo factual e objetivo de até 60 palavras sobre o conteúdo abaixo.

INSTRUÇÕES IMPORTANTES:
1. Relate apenas FATOS objetivos
2. NÃO use adjetivos elogiosos
3. PRESERVE O TEMPO VERBAL exatamente como aparece no texto original
4. NÃO mencione datas específicas (nem passadas nem futuras) - descreva apenas os eventos
5. Forneça APENAS o resumo, sem introduções

Texto:
{texto}"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Você é um analista de notícias que produz resumos factuais e neutros."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 200
                }
                
                response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=30)
                response.raise_for_status()
                resumo = response.json()["choices"][0]["message"]["content"].strip()
                
                # Limpar frases introdutórias
                resumo = limpar_frases_introdutorias(resumo)
                
                return resumo
                
            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout na tentativa {attempt + 1} para ID {id_noticia}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                else:
                    return f"[Erro: timeout ao gerar resumo para ID {id_noticia}]"
            except Exception as e:
                print(f"❌ Erro ao gerar resumo de 60 palavras para ID {id_noticia}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return f"[Erro ao gerar resumo para ID {id_noticia}]"
        
        return ""

    def agrupar_por_similaridade(resumos):
        """
        Agrupa resumos por similaridade temática usando o DeepSeek.
        Retorna lista de IDs de grupo para cada resumo.
        """
        import json
        
        N = len(resumos)
        if N == 1:
            return [1]
        
        # Prompt detalhado para agrupamento inteligente
        prompt = f"""
    TAREFA: Agrupe {N} resumos de notícias por SIMILARIDADE TEMÁTICA RELEVANTE.

    🚨 **PRIORIDADE MÁXIMA - EVENTOS IDÊNTICOS** (analise PRIMEIRO):
    1. Se MÚLTIPLAS notícias reportam o MESMO EVENTO FACTUAL (ex: "anúncio X em data Y", "análise Z publicada em data Y"), elas DEVEM ser agrupadas SEMPRE
    2. Variações de redação NÃO justificam separação se o evento central é o mesmo
    3. Diferentes ângulos jornalísticos do MESMO evento pertencem ao MESMO GRUPO
    4. **[IMPORTANTE] DATAS PRÓXIMAS NO MESMO MÊS**: Se notícias sobre a MESMA transação empresarial (mesmas empresas + mesmo tipo de operação) têm datas no mesmo período (ex: "25 de junho" vs "25 de novembro"), mas TODOS os outros detalhes são consistentes, considere que pode ser variação na data de divulgação ou erro de transcrição → AGRUPAR
    5. Exemplos práticos:
       - ✅ AGRUPAR: "JBS anuncia fusão em 25/11" + "JBS e Viva criam joint venture" + "Gigante do couro nasce de fusão JBS-Viva" → MESMO evento, datas próximas
       - ✅ AGRUPAR: "JBS cria JBS Viva 25/jun, 50% cada, 31 fábricas" + "JBS Viva anunciada 25/nov, 50% cada, 31 fábricas" → MESMO evento (detalhes idênticos, data pode variar)
       - ✅ AGRUPAR: "Itaú BBA eleva preço-alvo JBS para US$ 20" + "JBS deve subir 37% diz BBA" → MESMA análise financeira

    CRITÉRIOS SECUNDÁRIOS (aplicar APÓS verificar eventos idênticos):

    🎯 **REGRA GERAL**: 
    Agrupe quando as notícias compartilham o MESMO CONTEXTO OPERACIONAL ou EVENTO CORRELATO.
    Separe quando tratam de CONTEXTOS TEMPORAIS ou TEMÁTICOS DISTINTOS.

    ✅ **AGRUPAR QUANDO** (em ordem de prioridade):
    1. **MESMO EVENTO FACTUAL**: Múltiplas reportagens do mesmo acontecimento (mesmo se redação diferente)
    2. **Mesmo evento econômico + desdobramentos**: IPCA + Selic + projeções institucionais
    3. **Programa/política + implementação**: Decreto PAT + regras específicas + prazos
    4. **Transação específica + detalhes**: Aquisição + valores + empresas envolvidas
    5. **Sequência temporal direta**: Anúncio + resultados + desdobramentos imediatos
    6. **Diferentes aspectos do mesmo fato**: Medida governamental + impactos setoriais

    ❌ **SEPARAR QUANDO**:
    1. **Temporalidades desconectadas**: Evento histórico + fato recente sem relação direta
    2. **Áreas de negócio não relacionadas**: Operações comerciais + questões jurídicas independentes
    3. **Menção superficial mesma empresa**: Apenas citar mesma empresa em contextos distintos
    4. **Eventos independentes**: Investigação antitruste + programa governamental antigo

    TESTES DE DECISÃO PRÁTICOS:

    TESTE 1 - IDENTIDADE DE EVENTO (usar PRIMEIRO):
    "As notícias reportam o MESMO acontecimento factual (data, empresa, ação específica)?"
    - SIM → AGRUPAR OBRIGATORIAMENTE (ex: múltiplas reportagens de "fusão JBS-Viva 25/11")
    - NÃO → Aplicar TESTE 2

    TESTE 2 - COERÊNCIA TEMÁTICA (usar se TESTE 1 = NÃO):
    "Se remover a menção à empresa principal, as notícias ainda fazem sentido juntas?"
    - SIM → AGRUPAR (ex: políticas econômicas, programas governamentais)
    - NÃO → SEPARAR (ex: eventos históricos vs fatos recentes não relacionados)

    EXEMPLOS CONCRETOS:

    PRIORIDADE 1 - MESMO EVENTO (AGRUPAR SEMPRE):
    - ✅ MESMO GRUPO: "JBS anuncia fusão" + "JBS e Viva criam JBS Viva" + "Gigante do couro nasce" → mesmo evento (fusão 25/11)
    - ✅ MESMO GRUPO: "BBA eleva alvo JBS US$ 20" + "JBS deve subir 37%" → mesma análise financeira
    - ✅ MESMO GRUPO: "Avião J&F em Caracas domingo" + "Jato JBS pousa na Venezuela" → mesmo voo

    PRIORIDADE 2 - CONTEXTO CORRELATO:
    - ✅ MESMO GRUPO: "IPCA 0,09%" + "Selic 15%" + "PicPay revisa projeção" → contexto econômico correlato
    - ✅ MESMO GRUPO: "Decreto PAT" + "Taxas 3,6%" + "Interoperabilidade" → mesma política em implementação

    SEPARAR:
    - ❌ SEPARAR: "Estratégia campeãs nacionais 2010" + "Investigação EUA 2025" → temporalidades desconectadas
    - ❌ SEPARAR: "JBS compra empresa X" + "JBS em operação Carne Fraca 2017" → eventos independentes

    BALANCEAMENTO:
    - Evite agrupamento excessivo (não agrupe temas distintos)
    - Evite fragmentação excessiva (agrupe contextos correlatos)
    - Foque em IDENTIDADE DE EVENTO primeiro, COERÊNCIA TEMÁTICA depois

    FORMATO DE SAÍDA (OBRIGATÓRIO):
    {{"groups":[g1,g2,...,g{N}]}}

    Onde cada g é um número inteiro ≥1. Resumos no mesmo grupo devem ter o mesmo número.

    RESUMOS A AGRUPAR:
    """
        
        for i, resumo in enumerate(resumos, 1):
            prompt += f"\n{i}. {resumo}"
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            m = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    grupos = obj.get("groups", [])
                except json.JSONDecodeError as e:
                    print(f"⚠️ Erro ao parsear JSON: {e}")
                    grupos = []
            else:
                grupos = []
            
            if not grupos or len(grupos) != N:
                print(f"⚠️ Resposta inválida da API. Extraindo números como fallback...")
                nums = list(map(int, re.findall(r'\d+', content)))
                grupos = nums[:N] if len(nums) >= N else []
            
            if not grupos or len(grupos) != N:
                print(f"⚠️ Usando agrupamento sequencial (fallback total)")
                grupos = list(range(1, N + 1))
            
            if len(grupos) < N:
                grupos += [grupos[-1]] * (N - len(grupos))
            elif len(grupos) > N:
                grupos = grupos[:N]
            
            grupos_limpos = []
            for grupo in grupos:
                if isinstance(grupo, list):
                    grupos_limpos.append(grupo[0] if grupo else 1)
                elif isinstance(grupo, (int, float)):
                    grupos_limpos.append(int(grupo))
                else:
                    try:
                        grupos_limpos.append(int(str(grupo)))
                    except (ValueError, TypeError):
                        grupos_limpos.append(1)
            
            grupos_distintos = len(set(grupos_limpos))
            print(f"✅ Agrupamento concluído: {grupos_distintos} grupos distintos de {N} resumos")
            
            return grupos_limpos
            
        except Exception as e:
            print(f"❌ Erro ao agrupar resumos: {e}")
            import traceback
            traceback.print_exc()
            return list(range(1, N + 1))

    def agrupar_por_similaridade_original(resumos):
        import json, re
        N = len(resumos)
        prompt = (
            "Agrupe os resumos por similaridade de assunto.\n"
            "Considere como similar não apenas assuntos idênticos, "
            "mas também aqueles com forte relação temática, como diferentes aspectos de um mesmo setor, empresa ou impacto, "
            "mesmo que haja pequenas diferenças de redação ou detalhe. \n"
            f'Retorne **somente** uma linha em JSON, sem comentários nem markdown, exatamente assim:\n{{"groups":[g1,...,g{N}]}}\n'
            f"O array deve ter exatamente {N} inteiros (>=1). Nada além do JSON.\n\n"
        )
        for i, r in enumerate(resumos, 1):
            prompt += f"Resumo {i}: {r}\n"

        data = {"model": "deepseek-chat","messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":200}
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            m = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    grupos = obj.get("groups", [])
                except json.JSONDecodeError:
                    grupos = []
            else:
                grupos = []
            
            if not grupos or len(grupos) != N:
                nums = list(map(int, re.findall(r'\d+', content)))
                grupos = nums[:N] if len(nums) >= N else list(range(1, N+1))
            
            if len(grupos) < N:
                grupos += [grupos[-1]] * (N - len(grupos))
            elif len(grupos) > N:
                grupos = grupos[:N]
            
            # Garantir que todos os elementos sejam escalares
            grupos_limpos = []
            for grupo in grupos:
                if isinstance(grupo, list):
                    grupos_limpos.append(grupo[0] if grupo else 1)
                elif isinstance(grupo, (int, float)):
                    grupos_limpos.append(int(grupo))
                else:
                    try:
                        grupos_limpos.append(int(str(grupo)))
                    except (ValueError, TypeError):
                        grupos_limpos.append(1)
            
            return grupos_limpos
            
        except Exception as e:
            print(f"Erro ao agrupar resumos: {e}")
            return list(range(1, N+1))

    def gerar_resumo_120(textos, marca):
        corpo = "\n--- NOTÍCIA ---\n".join(textos)
        prompt = f"""INSTRUÇÕES IMPORTANTES:

1. Forneça APENAS o resumo consolidado, sem frases introdutórias.

2. NEUTRALIDADE OBRIGATÓRIA:
   - Relate apenas FATOS objetivos e verificáveis sobre a marca '{marca}'
   - NÃO use adjetivos elogiosos ou bajuladores (inovador, revolucionário, líder de mercado, excelente, incrível, extraordinário, disruptivo, etc.)
   - NÃO faça juízos de valor sobre a marca, seus produtos ou serviços
   - NÃO reproduza linguagem de marketing ou promocional das notícias originais
   - Mantenha tom jornalístico estritamente neutro e factual
   - Se a notícia contém críticas ou problemas, relate-os objetivamente sem suavizar

3. TRATAMENTO DE DATAS - REGRA CRÍTICA:
   - Para eventos JÁ OCORRIDOS (verbos no passado): NÃO mencione datas específicas
   - Para eventos FUTUROS (verbos no futuro): MANTENHA as datas
   
   Exemplos de REMOÇÃO (passado):
   ❌ "anunciou em 29/01/2026" → ✅ "anunciou"
   ❌ "afirmou em 29 de janeiro" → ✅ "afirmou"
   ❌ "informou nesta quinta-feira (29)" → ✅ "informou"
   ❌ "o banco lançou em 29 de janeiro" → ✅ "o banco lançou"
   
   Exemplos de MANUTENÇÃO (futuro):
   ✅ "previsto para 10 de fevereiro" → MANTER
   ✅ "deve ocorrer em 11 de fevereiro" → MANTER
   ✅ "a estreia acontecerá em 11 de fevereiro" → MANTER

4. FOCO EM FATOS:
   - O que aconteceu (ações concretas)
   - Dados numéricos e estatísticos
   - Anúncios, lançamentos, eventos específicos
   - Resultados financeiros ou operacionais mensuráveis

5. EVITE:
   - Opiniões sobre qualidade ou valor
   - Superlativos e exageros
   - Promessas ou expectativas futuras não confirmadas
   - Linguagem que soe como propaganda

Gere um resumo único de até 120 palavras consolidando as notícias a seguir sobre a marca '{marca}':

{corpo}"""
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um analista de notícias que produz resumos estritamente factuais e neutros. Você NÃO é um profissional de marketing ou relações públicas. Seu trabalho é consolidar informações de múltiplas notícias relatando apenas fatos objetivos, sem elogios, sem tom promocional, sem juízos de valor. Use linguagem jornalística neutra, direta e imparcial. Trate a marca como qualquer outra entidade noticiada, sem favorecimento. IMPORTANTE: Para eventos passados, NÃO mencione datas específicas. Para eventos futuros, MANTENHA as datas."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0,
            "max_tokens": 400
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data)
            response.raise_for_status()
            texto = response.json()["choices"][0]["message"]["content"].strip()

            # limpar cabeçalhos "** Resumo ... **"
            linhas = texto.split('\n')
            linhas_filtradas = []
            import re as _re
            for linha in linhas:
                linha_strip = linha.strip()
                if _re.match(r'^\*\*\s*resumo.*\*\*\s*$', linha_strip, _re.IGNORECASE):
                    print(f"🗑️ Removendo linha: {linha_strip}")
                    continue
                linhas_filtradas.append(linha)
            texto = '\n'.join(linhas_filtradas)
            texto = _re.sub(r"^\*\*[^*]*\*\*\s*", "", texto, flags=_re.IGNORECASE | _re.MULTILINE)
            texto = _re.sub(r"\*\(Exatamente\s*120\s*palavras\)\*|\*\(120\s*palavras\)\*", "", texto, flags=_re.IGNORECASE)
            texto = _re.sub(r"(\n\s*)+", "\n", texto.strip())
            
            # Aplicar limpeza de frases introdutórias antes de retornar
            texto_limpo = limpar_frases_introdutorias(texto.strip())
            
            # Corrigir datas que o DeepSeek possa ter inventado/expandido
            # Usar o corpo completo como "texto original" para extrair o contexto de datas
            try:
                texto_corrigido = corrigir_datas_inventadas(texto_limpo, corpo)
                # Validar que a função retornou uma string válida
                if not isinstance(texto_corrigido, str):
                    print(f"⚠️ AVISO: corrigir_datas_inventadas retornou tipo {type(texto_corrigido)}")
                    texto_corrigido = str(texto_corrigido)
            except Exception as e:
                print(f"⚠️ ERRO em corrigir_datas_inventadas: {e}")
                texto_corrigido = texto_limpo
            
            # ========== NOVA ETAPA: Remover datas passadas ==========
            try:
                texto_final = remover_datas_passadas(texto_corrigido)
                if not isinstance(texto_final, str):
                    print(f"⚠️ AVISO: remover_datas_passadas retornou tipo {type(texto_final)}")
                    texto_final = str(texto_final)
            except Exception as e:
                print(f"⚠️ ERRO em remover_datas_passadas: {e}")
                texto_final = texto_corrigido
            # =======================================================
            
            return texto_final
        except Exception as e:
            print(f"Erro ao gerar resumo final: {e}")
            return ""

    def gerar_resumo_consolidado_por_chunks(textos, marca):
        grupos = []
        grupo_atual = []
        total_chars = 0
        for texto in textos:
            if total_chars + len(texto) > LIMITE_CARACTERES_GRUPO and grupo_atual:
                grupos.append(grupo_atual)
                grupo_atual = []
                total_chars = 0
            grupo_atual.append(texto)
            total_chars += len(texto)
        if grupo_atual:
            grupos.append(grupo_atual)
        resumos_intermediarios = [gerar_resumo_120(grupo, marca) for grupo in grupos]
        if len(resumos_intermediarios) == 1:
            return resumos_intermediarios[0]
        else:
            print("🔗 Consolidando subgrupos em resumo final...")
            return gerar_resumo_120(resumos_intermediarios, marca)

    try:
        df = _normalize_df(arq_textos)
        df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

        todas_marcas = df['Canais'].dropna().unique().tolist()
        resultados = []

        for marca in todas_marcas:
            print(f"\n📄 Processando marca: {marca}")
            df_marca = df[df['Canais'] == marca].copy().reset_index(drop=True)

            resumos = [gerar_resumo_60(row['TextoCompleto'], row['Id']) for _, row in df_marca.iterrows()]
            df_marca['Resumo60'] = resumos

            grupos = agrupar_por_similaridade(resumos)
            
            # Validar que grupos é uma lista de escalares
            if not isinstance(grupos, list) or len(grupos) != len(resumos):
                print(f"⚠️ Erro nos grupos para marca {marca}. Usando grupos sequenciais.")
                grupos = list(range(1, len(resumos) + 1))
            
            # Verificar se algum elemento ainda é uma lista
            grupos_seguros = []
            for i, grupo in enumerate(grupos):
                if isinstance(grupo, list):
                    print(f"⚠️ Grupo {i} ainda é uma lista: {grupo}. Convertendo para {grupo[0] if grupo else i+1}")
                    grupos_seguros.append(grupo[0] if grupo else i+1)
                else:
                    grupos_seguros.append(grupo)
            
            df_marca['GrupoID'] = grupos_seguros
            df_marca['GrupoID'] = df_marca['GrupoID'].astype(str)

            for grupo_id, df_grupo in df_marca.groupby('GrupoID'):
                textos = df_grupo['TextoCompleto'].tolist()
                ids = df_grupo['Id'].astype(str).tolist()
                
                # ========== CORREÇÃO CRÍTICA: Garantir contagem consistente ==========
                # Limpar IDs antes de contar
                ids_limpos = [id_val.strip() for id_val in ids if id_val and str(id_val).strip()]
                qtd_noticias = len(ids_limpos)
                ids_para_salvar = ','.join(ids_limpos)  # Usar a mesma lista limpa
                
                # Debug: Verificar se a contagem está correta
                print(f"  📊 Grupo {grupo_id}: {qtd_noticias} notícia(s)")
                print(f"     IDs: {ids_para_salvar[:60]}{'...' if len(ids_para_salvar) > 60 else ''}")
                # ====================================================================
                
                resumo_final = gerar_resumo_consolidado_por_chunks(textos, marca)
                
                # ========== Adicionar prefixo com verbo (usando pool balanceado) ==========
                resumo_final = adicionar_prefixo_resumo(
                    resumo_final, 
                    qtd_noticias, 
                    verbos_singular, 
                    verbos_plural,
                    pool_verbos  # ← Passar o pool para distribuição balanceada
                )
                
                # Debug: Mostrar qual verbo foi usado E VALIDAR
                primeiro_verbo = ' '.join(resumo_final.split()[0:3])
                
                # Detectar se o verbo usado é realmente singular ou plural
                verbo_real_tipo = None
                for v in verbos_singular:
                    if resumo_final.startswith(v + " "):
                        verbo_real_tipo = "SINGULAR"
                        break
                if not verbo_real_tipo:
                    for v in verbos_plural:
                        if resumo_final.startswith(v + " "):
                            verbo_real_tipo = "PLURAL"
                            break
                
                tipo_esperado = "SINGULAR" if qtd_noticias == 1 else "PLURAL"
                
                if verbo_real_tipo != tipo_esperado:
                    print(f"  ❌ ERRO: Esperado {tipo_esperado} mas usou {verbo_real_tipo}!")
                    print(f"     Verbo aplicado: '{primeiro_verbo}'")
                else:
                    print(f"  ✅ Verbo: '{primeiro_verbo}' ({tipo_esperado}) - CORRETO")
                # ==========================================================================
                
                resultados.append({
                    "Marca": marca,
                    "GrupoID": f"{marca}_G{grupo_id}",
                    "QtdNoticias": qtd_noticias,  # Usar a contagem limpa
                    "Ids": ids_para_salvar,  # Usar a string limpa
                    "Resumo": resumo_final
                })

        df_final = pd.DataFrame(resultados, columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])

        # Short URLs
        try:
            import pyshorteners
            s = pyshorteners.Shortener()
            short_urls = []
            print("🔗 Gerando ShortURLs para todas as notícias...")
            for _, row in df.iterrows():
                url = row.get('UrlVisualizacao', '')
                try:
                    short_url = s.tinyurl.short(url) if url else ''
                except Exception as e:
                    print(f"⚠️ Erro ao encurtar URL para ID {row.get('Id')}: {e}")
                    short_url = url
                short_urls.append(short_url)
            df['ShortURL'] = short_urls
        except Exception as e:
            print(f"⚠️ Falha ao carregar/usar pyshorteners: {e}")
            if 'ShortURL' not in df.columns:
                df['ShortURL'] = df.get('UrlVisualizacao', '')

        df[['Id', 'Canais', 'ShortURL']].to_excel('dados/api/shorturls_por_id.xlsx', index=False)
        print("✅ Arquivo shorturls_por_id.xlsx salvo com ShortURLs.")

        # Limpezas no texto do resumo
        if not df_final.empty and 'Resumo' in df_final.columns:
            df_final['Resumo'] = df_final['Resumo'].astype(str).str.replace('*', '', regex=False)
            df_final = df_final[~df_final['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]
            for marca in w_marcas:
                df_final['Resumo'] = df_final['Resumo'].str.replace(f"(?i)\\b{re.escape(marca)}\\b", f"*{marca}*", regex=True)
        
        # ========== PÓS-PROCESSAMENTO: Validação de verbos ==========
        df_final = pos_processar_validacao_verbos(df_final, verbos_singular, verbos_plural)
        # ===========================================================

        print(f"\n✅ Processamento concluído! {len(df_final)} resumos gerados com prefixos e datas tratadas.")
        return df_final

    except Exception as e:
        import traceback as _tb
        print(f"Erro geral no processamento: {e}")
        print(_tb.format_exc(limit=1))
        return pd.DataFrame(columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])


# ========== ALIAS PARA COMPATIBILIDADE COM CÓDIGO ANTIGO ==========
def agrupar_noticias_por_similaridade(arq_textos):
    """
    Alias para processar_marcas_v2() - mantido para compatibilidade com código existente.
    
    Esta função é um wrapper que chama processar_marcas_v2 com o mesmo comportamento.
    Mantida para não quebrar imports em outros módulos (ex: main_menu.py).
    """
    return processar_marcas_v2(arq_textos)