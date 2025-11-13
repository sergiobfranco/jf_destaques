# Etapa 2: Resumo de até 60 palavras, agrupamento semântico e geração de resumos finais com refinamento por subtemas
# Versão 4: Adicionado prefixo automático com verbos do DOCX (singular/plural) baseado em QtdNoticias
# Data: 21/10/2025

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
                print(f"   ⚠️ Verbo '{verbo_usado}' não encontrado no mapeamento para substituição")
            
            # 5. Atualizar QtdNoticias se estiver incorreto
            if qtd_declarada != qtd_real:
                df.at[idx, 'QtdNoticias'] = qtd_real
                print(f"   ✅ QtdNoticias atualizado: {qtd_declarada} → {qtd_real}")
    
    print(f"\n✅ Pós-processamento concluído: {correcoes_realizadas} correção(ões) realizada(s)")
    print("=" * 60)
    
    return df


def obter_verbos_padrao():
    """
    Verbos de fallback caso o DOCX não possa ser lido
    """
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


def agrupar_noticias_por_similaridade(arq_textos):
    api_key = obter_chave_deepseek()

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    LIMITE_CARACTERES_GRUPO = 12000

    # Carregar verbos uma única vez
    verbos_singular, verbos_plural = carregar_verbos_iniciais()
    
    # DEBUG CRÍTICO: Verificar se os verbos foram classificados corretamente
    print("\n🔍 === VERIFICAÇÃO DE VERBOS CARREGADOS ===")
    print(f"Verbos SINGULAR ({len(verbos_singular)}):")
    for v in verbos_singular:
        print(f"  - {v}")
    print(f"\nVerbos PLURAL ({len(verbos_plural)}):")
    for v in verbos_plural:
        print(f"  - {v}")
    print("=" * 60)
    
    # Criar pools de verbos embaralhados (Opção A - distribuição balanceada)
    pool_verbos = {
        'singular': verbos_singular.copy(),
        'plural': verbos_plural.copy()
    }
    random.shuffle(pool_verbos['singular'])
    random.shuffle(pool_verbos['plural'])
    print(f"🎲 Pools de verbos inicializados e embaralhados\n")

    # ================= NORMALIZAÇÃO CRÍTICA =================
    def _normalize_df(df_in):
        """
        - Converte Canais (lista -> string) para evitar 'unhashable type: list'
        - Garante Id como inteiro -> string (consistente com o restante do fluxo)
        """
        if df_in is None:
            return pd.DataFrame(columns=["Id", "Titulo", "Conteudo", "Canais", "UrlVisualizacao"])
        df = df_in.copy()

        if 'Canais' in df.columns:
            def _to_str(v):
                if isinstance(v, list):
                    if len(v) == 1:
                        return str(v[0])
                    return ', '.join(map(str, v))
                return '' if pd.isna(v) else str(v)
            df['Canais'] = df['Canais'].apply(_to_str)

        if 'Id' in df.columns:
            df['Id'] = pd.to_numeric(df['Id'], errors='ignore')
            try:
                df['Id'] = pd.to_numeric(df['Id'], errors='coerce').astype('Int64')
                df = df.dropna(subset=['Id']).copy()
                df['Id'] = df['Id'].astype(int).astype(str)
            except Exception:
                df['Id'] = df['Id'].astype(str)

        return df

    def gerar_resumo_60(texto, id_):
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
        
        for tentativa in range(3):
            try:
                print(f"📝 Gerando resumo curto para notícia ID: {id_}...")
                prompt = """INSTRUÇÕES IMPORTANTES:

1. Forneça APENAS o resumo da notícia, sem frases introdutórias como "aqui está um resumo", "baseado no texto fornecido", etc.

2. NEUTRALIDADE OBRIGATÓRIA:
   - Relate apenas FATOS objetivos e verificáveis
   - NÃO use adjetivos elogiosos ou bajuladores (inovador, revolucionário, líder, excelente, incrível, extraordinário, etc.)
   - NÃO faça juízos de valor sobre a marca ou seus produtos
   - NÃO reproduza linguagem de marketing ou promocional presente no texto original
   - Mantenha tom jornalístico neutro e factual

3. FOCO:
   - O que aconteceu (fatos)
   - Quando aconteceu
   - Quem estava envolvido
   - Dados e números concretos

Resuma o conteúdo a seguir em até 60 palavras:

""" + texto
                data = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Você é um analista de notícias que produz resumos estritamente factuais e neutros. Você NÃO é um profissional de marketing ou relações públicas. Seu trabalho é relatar fatos objetivamente, sem elogios, sem tom promocional, sem juízos de valor. Use linguagem jornalística neutra e direta."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0,
                    "max_tokens": 120
                }
                r = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=45)
                r.raise_for_status()
                out = r.json()["choices"][0]["message"]["content"].strip()
                if out:
                    # Aplicar limpeza de frases introdutórias antes de retornar
                    return limpar_frases_introdutorias(out)
            except Exception as e:
                print(f"Resumo60 falhou (tentativa {tentativa+1}) ID {id_}: {e}")
                time.sleep(1 + tentativa)
        # fallback barato
        titulo_e_conteudo = texto[:2000]
        return titulo_e_conteudo[:260]

    def agrupar_por_similaridade(resumos):
        """
        Agrupa resumos semanticamente relacionados com critérios explícitos.
        Retorna lista de IDs de grupo (1 a N) para cada resumo.
        """
        import json
        import re
        
        N = len(resumos)
        
        # PROMPT APRIMORADO COM CRITÉRIOS EXPLÍCITOS
        prompt = f"""Você é um especialista em análise de notícias corporativas.

    TAREFA: Agrupe {N} resumos de notícias por SIMILARIDADE SEMÂNTICA FORTE.

    CRITÉRIOS DE AGRUPAMENTO (em ordem de prioridade):
    1. **Mesmo evento/transação específica**: Se mencionam a mesma aquisição, mesmo valor financeiro, mesmas empresas envolvidas → MESMO GRUPO
    2. **Mesmo escândalo/acontecimento histórico**: Se citam o mesmo evento passado (ex: "Joesley Day", "escândalo de 2017") → MESMO GRUPO
    3. **Mesma empresa + mesmo contexto**: Se falam da mesma holding/empresa no mesmo contexto temporal (ex: J&F e energia nuclear) → MESMO GRUPO
    4. **Progressão temporal do mesmo assunto**: Notícias que são continuação/desdobramento uma da outra → MESMO GRUPO

    IMPORTANTE:
    - Ignore pequenas diferenças de redação
    - Foque nos FATOS CENTRAIS, não em detalhes secundários
    - Seja AGRESSIVO no agrupamento: se há 80%+ de sobreposição temática, agrupe
    - Notícias sobre setores diferentes da mesma empresa devem ficar em grupos separados

    EXEMPLOS:
    - "J&F compra Eletronuclear por R$ 535 mi" + "Irmãos Batista adquirem participação na Eletronuclear" → MESMO GRUPO
    - "Escândalo Joesley Day em 2017" + "Irmãos Batista absolvidos após Joesley Day" → MESMO GRUPO
    - "JBS tem queda nas ações" + "J&F compra Eletronuclear" → GRUPOS DIFERENTES (assuntos distintos)

    FORMATO DE SAÍDA (OBRIGATÓRIO):
    Retorne APENAS uma linha JSON válida, sem comentários, markdown ou texto adicional:
    {{"groups":[g1,g2,...,g{N}]}}

    Onde cada g é um número inteiro ≥1. Resumos no mesmo grupo devem ter o mesmo número.

    RESUMOS A AGRUPAR:
    """
        
        for i, resumo in enumerate(resumos, 1):
            prompt += f"\n{i}. {resumo}"
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Aumentado de 0 para permitir mais criatividade
            "max_tokens": 300    # Aumentado para acomodar respostas maiores
        }
        
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            
            # Parser robusto para extrair JSON
            m = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    grupos = obj.get("groups", [])
                except json.JSONDecodeError as e:
                    print(f"⚠️ Erro ao parsear JSON: {e}")
                    grupos = []
            else:
                # Fallback: tentar extrair números diretamente
                grupos = []
            
            # Validação e normalização dos grupos
            if not grupos or len(grupos) != N:
                print(f"⚠️ Resposta inválida da API. Extraindo números como fallback...")
                nums = list(map(int, re.findall(r'\d+', content)))
                grupos = nums[:N] if len(nums) >= N else []
            
            # Se ainda falhar, usa agrupamento sequencial
            if not grupos or len(grupos) != N:
                print(f"⚠️ Usando agrupamento sequencial (fallback total)")
                grupos = list(range(1, N + 1))
            
            # Ajustar comprimento se necessário
            if len(grupos) < N:
                grupos += [grupos[-1]] * (N - len(grupos))
            elif len(grupos) > N:
                grupos = grupos[:N]
            
            # Normalizar para escalares (resolver problema de listas aninhadas)
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
            
            # LOG para debug
            print(f"✅ Agrupamento concluído: {len(set(grupos_limpos))} grupos distintos de {N} resumos")
            
            return grupos_limpos
            
        except Exception as e:
            print(f"❌ Erro ao agrupar resumos: {e}")
            traceback.print_exc()
            return list(range(1, N + 1))  # Fallback: cada resumo em grupo separado

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
            resp = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data); resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            m = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    grupos = obj.get("groups", [])
                except Exception:
                    grupos = []
            else:
                grupos = []
            if not grupos:
                nums = list(map(int, re.findall(r'\d+', content)))
                grupos = nums[:N]
            if not grupos:
                grupos = list(range(1, N+1))
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

3. FOCO EM FATOS:
   - O que aconteceu (ações concretas)
   - Quando aconteceu (datas, períodos)
   - Dados numéricos e estatísticos
   - Anúncios, lançamentos, eventos específicos
   - Resultados financeiros ou operacionais mensuráveis

4. EVITE:
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
                    "content": "Você é um analista de notícias que produz resumos estritamente factuais e neutros. Você NÃO é um profissional de marketing ou relações públicas. Seu trabalho é consolidar informações de múltiplas notícias relatando apenas fatos objetivos, sem elogios, sem tom promocional, sem juízos de valor. Use linguagem jornalística neutra, direta e imparcial. Trate a marca como qualquer outra entidade noticiada, sem favorecimento."
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
            return limpar_frases_introdutorias(texto.strip())
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

        print(f"\n✅ Processamento concluído! {len(df_final)} resumos gerados com prefixos.")
        return df_final

    except Exception as e:
        import traceback as _tb
        print(f"Erro geral no processamento: {e}")
        print(_tb.format_exc(limit=1))
        return pd.DataFrame(columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])