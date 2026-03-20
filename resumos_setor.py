# Rotina para gerar os resumos de Setor pelo DeepSeek

import pandas as pd
import requests
import time
import configparser
import os
import traceback
import re

from dotenv import load_dotenv

def obter_chave_deepseek():
    # Caminho absoluto do .env com base no local do script
    #base_dir = os.path.dirname(os.path.abspath(__file__))
    #env_path = os.path.join(base_dir, ".env")
    #load_dotenv(env_path)

    load_dotenv()

    # Caminho correto para o config_usuario.ini em dados/config/
    config_path = os.path.join("dados", "config", "config_usuario.ini")

    # Debug opcional
    print(f"🛠️ Lendo config de: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    perfil = config.get("usuario", "perfil", fallback="client").strip().lower()

    env_var = f"DEEPSEEK_API_KEY_{perfil.upper()}"
    chave = os.getenv(env_var)

    # Diagnóstico
    print(f"Perfil de usuário: {perfil}")
    print(f"Variável de ambiente esperada: {env_var}")
    print(f"Chave encontrada: {chave[:10]}..." if chave else "❌ Nenhuma chave encontrada")
    # Diagnóstico adicional opcional
    # traceback.print_stack(limit=2)

    if not chave:
        raise ValueError(f"Chave de API não encontrada para o perfil '{perfil}' ({env_var}) no arquivo .env")
    
    return chave

from config import DEEPSEEK_API_URL, w_marcas

# ================= NOVA FUNÇÃO: PRÉ-PROCESSAMENTO BOLSONARO =================
def reclassificar_noticias_bolsonaro(df):
    """
    Pré-processa notícias classificadas como POLÍTICA para verificar se tratam
    da condenação/prisão do ex-presidente Bolsonaro. Se sim, reclassifica para JUSTIÇA.
    """
    api_key = obter_chave_deepseek()
    
    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prompt de análise baseado no documento fornecido
    PROMPT_ANALISE = """**INSTRUÇÃO PRINCIPAL:**

Você é um especialista em classificação de notícias e sua tarefa é realizar um pós-processamento de uma notícia classificada como "POLÍTICA".

Seu objetivo é reclassificar a notícia para o tema **"JUSTIÇA"** SE E SOMENTE SE o seu conteúdo tratar, de forma *central e principal*, do processo legal, condenação e/ou prisão do ex-presidente Jair Bolsonaro. Em todos os outros casos, a classificação deve permanecer **"POLÍTICA"**.

**REQUISITOS DE CONTEÚDO (Aspectos Chave para Classificação 'JUSTIÇA'):**

Para reclassificar para "JUSTIÇA", a notícia deve conter menções claras e centrais a um ou mais dos seguintes aspectos legais e judiciais relacionados ao ex-presidente:

1. **Ações Judiciais e Processos:** Menção a inquéritos, denúncias formais, julgamentos em instâncias superiores (como STF ou TSE), ou qualquer processo legal em andamento ou finalizado.

2. **Decisões Judiciais:** Referência explícita a sentenças, condenações (em qualquer instância), cassação de direitos políticos ou ordens de prisão.

3. **Execução da Pena:** Detalhes sobre a prisão, cumprimento de pena, regime carcerário, ou recursos jurídicos relacionados à detenção.

4. **Envolvimento de Órgãos Judiciais:** Citações a ministros/juízes específicos (em relação direta ao caso), Procuradoria-Geral da República (PGR) ou decisões de plenários de tribunais.

**TEXTO DA NOTÍCIA PARA ANÁLISE:**

---

{NOTICIA}

---

**FORMATO DE SAÍDA OBRIGATÓRIO:**

Sua resposta deve ser **SOMENTE** a nova classificação. Não inclua nenhuma explicação, introdução ou texto adicional.

* Se a notícia atender aos requisitos e tratar do caso de condenação/prisão do ex-presidente: **JUSTIÇA**

* Se a notícia tratar de outros temas políticos (reforma ministerial, eleições, votações no congresso, etc.): **POLÍTICA**

**RESPOSTA (Apenas a palavra da categoria):**"""

    def extrair_noticia_do_prompt(prompt_text):
        """Extrai o texto da notícia após o primeiro ':' (dois pontos)"""
        if pd.isna(prompt_text) or not prompt_text:
            return ""
        
        prompt_str = str(prompt_text)
        idx = prompt_str.find(':')
        
        if idx != -1:
            return prompt_str[idx + 1:].strip()
        
        return prompt_str.strip()
    
    def analisar_noticia(noticia_text, row_id=""):
        """Envia notícia para análise do DeepSeek e retorna a classificação"""
        if not noticia_text or len(noticia_text) < 50:
            print(f"⚠️ Notícia muito curta ou vazia (ID: {row_id}), mantendo POLÍTICA")
            return "POLÍTICA"
        
        prompt_completo = PROMPT_ANALISE.replace("{NOTICIA}", noticia_text)
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Você é um especialista em classificação de notícias jurídicas e políticas."},
                {"role": "user", "content": prompt_completo}
            ],
            "temperature": 0.3  # Temperatura baixa para respostas mais consistentes
        }
        
        # Retry com backoff
        for tentativa in range(3):
            try:
                print(f"🔍 Analisando notícia (ID: {row_id}) - Tentativa {tentativa + 1}")
                response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=payload, timeout=60)
                response.raise_for_status()
                resultado = response.json()['choices'][0]['message']['content'].strip().upper()
                
                # Validar resposta
                if "JUSTIÇA" in resultado or "JUSTICA" in resultado:
                    return "JUSTIÇA"
                elif "POLÍTICA" in resultado or "POLITICA" in resultado:
                    return "POLÍTICA"
                else:
                    print(f"⚠️ Resposta inesperada: '{resultado}', assumindo POLÍTICA")
                    return "POLÍTICA"
                    
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout na tentativa {tentativa + 1}")
                time.sleep(2 * (tentativa + 1))
            except requests.exceptions.RequestException as e:
                print(f"🔌 Erro de conexão na tentativa {tentativa + 1}: {e}")
                time.sleep(2 * (tentativa + 1))
            except (KeyError, IndexError) as e:
                print(f"🔧 Erro na estrutura da resposta: {e}")
                break
            except Exception as e:
                print(f"❌ Erro inesperado na tentativa {tentativa + 1}: {e}")
                time.sleep(1 * (tentativa + 1))
        
        # Se todas as tentativas falharam, manter classificação original
        print(f"⚠️ Falha ao analisar notícia (ID: {row_id}), mantendo POLÍTICA")
        return "POLÍTICA"
    
    try:
        if df is None or df.empty:
            print("⚠️ DataFrame vazio, pulando pré-processamento")
            return df
        
        # Filtrar apenas notícias classificadas como POLÍTICA
        df_politica = df[df['Tema'].str.upper().str.strip() == 'POLÍTICA'].copy()
        
        if df_politica.empty:
            print("ℹ️ Nenhuma notícia classificada como POLÍTICA encontrada")
            return df
        
        print(f"\n{'='*60}")
        print(f"🔄 INICIANDO PRÉ-PROCESSAMENTO - RECLASSIFICAÇÃO BOLSONARO")
        print(f"{'='*60}")
        print(f"📊 Total de notícias POLÍTICA a analisar: {len(df_politica)}\n")
        
        reclassificadas = 0
        
        for idx, row in df_politica.iterrows():
            # Extrair informações
            prompt_completo = row.get('Prompt', '')
            row_id = str(row.get('Ids', row.get('Id', f'id_{idx}'))).strip()
            
            # Extrair texto da notícia
            noticia = extrair_noticia_do_prompt(prompt_completo)
            
            if not noticia:
                print(f"⚠️ Não foi possível extrair notícia do prompt (ID: {row_id})")
                continue
            
            print(f"\n{'─'*60}")
            print(f"📰 Analisando notícia {reclassificadas + 1}/{len(df_politica)}")
            print(f"   ID: {row_id}")
            print(f"   Preview: {noticia[:100]}...")
            
            # Analisar e obter nova classificação
            nova_classificacao = analisar_noticia(noticia, row_id)
            
            # Se foi reclassificada para JUSTIÇA, atualizar no DataFrame original
            if nova_classificacao == "JUSTIÇA":
                df.at[idx, 'Tema'] = "JUSTIÇA"
                reclassificadas += 1
                print(f"✅ RECLASSIFICADA: POLÍTICA → JUSTIÇA")
            else:
                print(f"➡️ Mantida como: POLÍTICA")
            
            # Pausa para respeitar limites da API
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"✅ PRÉ-PROCESSAMENTO CONCLUÍDO")
        print(f"{'='*60}")
        print(f"📊 Total analisadas: {len(df_politica)}")
        print(f"🔄 Reclassificadas para JUSTIÇA: {reclassificadas}")
        print(f"➡️ Mantidas como POLÍTICA: {len(df_politica) - reclassificadas}")
        print(f"{'='*60}\n")
        
        return df
        
    except Exception as e:
        print(f"❌ Erro no pré-processamento de reclassificação: {e}")
        traceback.print_exc()
        return df  # Retorna DataFrame original em caso de erro

# ================= FIM NOVA FUNÇÃO =================


def remover_datas_passadas(texto_resumo):
    if not texto_resumo:
        return texto_resumo

    meses = r'(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
    dias_semana = r'(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:-feira)?'

    # proteger datas futuras
    texto_modificado = re.sub(
        r'\b(previsto para|prevista para|programado para|deve ocorrer em|ocorrerá em|acontecerá em|será em|será no dia|marcado para|agendado para)\s+(\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?)',
        r'__PROTEGER_DATA__\1 \2__FIM_PROTECAO__',
        texto_resumo,
        flags=re.IGNORECASE
    )

    texto_modificado = re.sub(
        r'\b(no próximo|na próxima|próximo|próxima)\s+(dia|'+dias_semana+r')?\s*(\d{1,2}(?:\s+de\s+'+meses+r'(?:\s+de\s+\d{4})?)?)',
        r'__PROTEGER_DATA__\1 \2 \3__FIM_PROTECAO__',
        texto_modificado,
        flags=re.IGNORECASE
    )

    verbos_passado = r'(?:anunciou|informou|divulgou|publicou|comunicou|reportou|declarou|afirmou|revelou|confirmou|lançou|apresentou|mostrou|indicou|condenou|condenaram|pautou|pautaram|decidiu|decidiram|aprovou|aprovaram|realizou|realizaram|registrou|registraram|assinou|assinaram|entregou|entregaram|enviou|enviaram|recebeu|receberam|aceitou|aceitaram|rejeitou|rejeitaram|negou|negaram|admitiu|admitiram|reconheceu|reconheceram|criticou|criticaram|acusou|acusaram|denunciou|denunciaram|investigou|investigaram|descobriu|descobriram|encontrou|encontraram|identificou|identificaram|descartou|descartaram)'

    padrao_verbo_data = r'\b(' + verbos_passado + r')\s*,?\s*(?:em\s+|no\s+|na\s+|dia\s+|nesta\s+|desta\s+|naquele\s+|daquele\s+|nessa\s+|desse\s+|naquela\s+|daquela\s+)?\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\s*,?'
    texto_modificado = re.sub(padrao_verbo_data, r'\1', texto_modificado, flags=re.IGNORECASE)

    padrao_data_extenso = r'\b(?:em|dia|no dia|na data|nesta|nesta data|neste dia)\s+\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b'
    texto_modificado = re.sub(padrao_data_extenso, '', texto_modificado, flags=re.IGNORECASE)

    padrao_dia_semana = r'\b(?:nesta|neste|na|no|desta|deste|da|do|última|último)\s+' + dias_semana + r'\s*\(\d{1,2}\)'
    texto_modificado = re.sub(padrao_dia_semana, '', texto_modificado, flags=re.IGNORECASE)

    texto_modificado = re.sub(r'\s{2,}', ' ', texto_modificado)
    texto_modificado = re.sub(r'^\s*,\s*', '', texto_modificado)
    texto_modificado = re.sub(r'\s+,', ',', texto_modificado)
    texto_modificado = re.sub(r',\s*,', ',', texto_modificado)
    texto_modificado = re.sub(r'__PROTEGER_DATA__', '', texto_modificado)
    texto_modificado = re.sub(r'__FIM_PROTECAO__', '', texto_modificado)

    return texto_modificado.strip()


def remover_datas_nao_presentes_no_original(texto_resumo, texto_original):
    if not texto_resumo or not texto_original:
        return texto_resumo

    meses = r'(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
    padroes_original = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        r'\b\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b',
        r'\b(?:nesta|desta|na|no)\s+(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:-feira)?\s*\(\d{1,2}\)\b',
        r'\bamanhã\s*,?\s*\d{1,2}\b'
    ]

    datas_no_original = set()
    for padrao in padroes_original:
        matches = re.findall(padrao, texto_original, re.IGNORECASE)
        datas_no_original.update(matches)

    texto_modificado = texto_resumo
    padroes_resumo = [
        (r'\b\d{1,2}/\d{1,2}/\d{4}\b', lambda m: m.group(0)),
        (r'\b\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b', lambda m: m.group(0)),
        (r'\b(?:em|dia|no dia|na data|nesta|neste)\s+\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b', lambda m: re.sub(r'^\b(?:em|dia|no dia|na data|nesta|neste)\s+', '', m.group(0), flags=re.IGNORECASE))
    ]

    for padrao, extrator in padroes_resumo:
        for match in re.finditer(padrao, texto_modificado, re.IGNORECASE):
            data_resumo = extrator(match)
            if data_resumo not in datas_no_original:
                texto_modificado = re.sub(r'(?:\b(?:em|no|na|no dia|na data|dia)\b\s*)?' + re.escape(match.group(0)) + r'(?:,)?', '', texto_modificado, flags=re.IGNORECASE)

    texto_modificado = re.sub(r'\s{2,}', ' ', texto_modificado)
    texto_modificado = re.sub(r'^\s*,\s*', '', texto_modificado)
    texto_modificado = re.sub(r'\s+,\s*', ', ', texto_modificado)

    return texto_modificado.strip()


def corrigir_datas_inventadas(texto_resumo, texto_original):
    if not texto_resumo:
        return texto_resumo

    meses = r'(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'

    datas_originais = set(re.findall(r'\b\d{1,2}/\d{1,2}/\d{4}\b', texto_original))
    datas_originais.update(re.findall(r'\b\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b', texto_original, re.IGNORECASE))
    dias_semana_orig = set(re.findall(r'\b(?:nesta|desta|na|no)\s+(?:segunda(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sábado(?:-feira)?|domingo(?:-feira)?)\s*\((\d{1,2})\)', texto_original, re.IGNORECASE))

    texto_corrigido = texto_resumo

    def _substituir_dia_mes(match):
        dia = match.group(1)
        mes = match.group(2)
        if f"{dia} de {mes}".lower() in (d.lower() for d in datas_originais):
            return match.group(0)
        if dia in dias_semana_orig:
            return f"{mes}"
        return f"{mes}"

    texto_corrigido = re.sub(r'\b(\d{1,2})\s+de\s+(' + meses + r')(?:\s+de\s+\d{4})?\b', _substituir_dia_mes, texto_corrigido, flags=re.IGNORECASE)

    def _remover_data_completa(match):
        data = match.group(0)
        return data if data in datas_originais else ''

    texto_corrigido = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', _remover_data_completa, texto_corrigido)

    texto_corrigido = re.sub(r'\b(?:segunda(?:-feira)?|terça(?:-feira)?|quarta(?:-feira)?|quinta(?:-feira)?|sexta(?:-feira)?|sábado(?:-feira)?|domingo(?:-feira)?)\s*,?\s*\d{1,2}\s+de\s+' + meses + r'(?:\s+de\s+\d{4})?\b', '', texto_corrigido, flags=re.IGNORECASE)
    texto_corrigido = re.sub(r'\s{2,}', ' ', texto_corrigido)
    texto_corrigido = re.sub(r'^\s*,\s*', '', texto_corrigido)
    texto_corrigido = re.sub(r'\s+,\s*', ', ', texto_corrigido)

    return texto_corrigido.strip()


# Função gerar_resumos_setor com proteções adicionais

def gerar_resumos_setor(df):
    api_key = obter_chave_deepseek()

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }    
    
    # ================= NORMALIZAÇÃO PREVENTIVA (NOVO) =================
    def _normalize_setor_df(df_in):
        """
        Normaliza campos que podem vir como lista para evitar problemas
        """
        if df_in is None or df_in.empty:
            return pd.DataFrame(columns=["Id", "Tipo", "Prompt", "Tema", "RelevanceScore", "IdVeiculo", "Ids"])
        
        df = df_in.copy()
        
        # Normalizar campos que podem ser listas
        campos_para_normalizar = ['Tema', 'Id', 'Ids', 'Tipo']
        
        for campo in campos_para_normalizar:
            if campo in df.columns:
                def _normalize_field(v):
                    if isinstance(v, list):
                        if len(v) == 1:
                            return str(v[0])
                        elif len(v) > 1:
                            return ', '.join(map(str, v))
                        else:
                            return ''
                    return '' if pd.isna(v) else str(v)
                
                df[campo] = df[campo].apply(_normalize_field)
                print(f"✅ Campo '{campo}' normalizado")
        
        return df
    # ===============================================================

    def resumir_prompt(prompt_text, tema="", row_id=""):
        # Adicionar instrução explícita para evitar frases introdutórias E neutralidade
        prompt_completo = f"""INSTRUÇÕES IMPORTANTES:

1. Forneça APENAS o resumo, sem frases introdutórias como "aqui está um resumo", "baseado no texto fornecido", "o resumo é", ou similares.

2. NEUTRALIDADE OBRIGATÓRIA:
   - Relate apenas FATOS objetivos e verificáveis
   - NÃO use adjetivos elogiosos ou bajuladores (inovador, revolucionário, líder, excelente, incrível, extraordinário, etc.)
   - NÃO faça juízos de valor sobre marcas, empresas ou entidades
   - NÃO reproduza linguagem de marketing ou promocional presente no texto original
   - Mantenha tom jornalístico neutro e factual
   - Se há críticas ou problemas, relate-os objetivamente sem suavizar

3. FOCO EM FATOS:
   - O que aconteceu (ações concretas)
   - Quando aconteceu (datas, períodos)
   - Dados numéricos e estatísticos
   - Anúncios, eventos específicos
   - Resultados mensuráveis

{prompt_text}"""
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "Você é um analista de notícias que produz resumos estritamente factuais e neutros. Você NÃO é um profissional de marketing ou relações públicas. Seu trabalho é relatar fatos objetivamente sobre qualquer tema ou setor, sem elogios, sem tom promocional, sem juízos de valor. Use linguagem jornalística neutra, direta e imparcial."
                },
                {
                    "role": "user", 
                    "content": prompt_completo
                }
            ],
            "temperature": 0.7
        }
        
        def limpar_frases_introdutorias(texto):
            """Remove frases introdutórias comuns que o LLM pode adicionar"""
            if not texto:
                return texto
            
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
            
            texto_limpo = texto.strip()
            for padrao in padroes_remover:
                texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE)
            
            return texto_limpo.strip()

        # Implementar retry com backoff
        for tentativa in range(3):
            try:
                print(f"🔄 Tentativa {tentativa + 1} para tema: {tema} (ID: {row_id})")
                response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=payload, timeout=60)
                response.raise_for_status()
                resultado = response.json()['choices'][0]['message']['content']
                
                # Verificar se o resultado não está vazio
                if resultado and resultado.strip():
                    # Aplicar limpeza de frases introdutórias antes de seguir
                    texto = limpar_frases_introdutorias(resultado)

                    # Aplicar correções de datas: remover inventadas, remover passadas, validar original
                    texto = corrigir_datas_inventadas(texto, prompt_completo)
                    texto = remover_datas_passadas(texto)
                    texto = remover_datas_nao_presentes_no_original(texto, prompt_completo)

                    return texto.strip()
                else:
                    print(f"⚠️ Resposta vazia na tentativa {tentativa + 1}")
                    
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout na tentativa {tentativa + 1} para {tema}")
                time.sleep(2 * (tentativa + 1))
            except requests.exceptions.RequestException as e:
                print(f"🔌 Erro de conexão na tentativa {tentativa + 1}: {e}")
                time.sleep(2 * (tentativa + 1))
            except KeyError as e:
                print(f"🔧 Erro na estrutura da resposta: {e}")
                break
            except Exception as e:
                print(f"❌ Erro inesperado na tentativa {tentativa + 1}: {e}")
                time.sleep(1 * (tentativa + 1))
        
        # Fallback se todas as tentativas falharam
        return f"Erro: Não foi possível gerar resumo para o tema '{tema}' após 3 tentativas."

    try:
        # ================= CHAMAR PRÉ-PROCESSAMENTO AQUI =================
        print("\n🚀 Iniciando processamento completo...")
        df = reclassificar_noticias_bolsonaro(df)
        print("\n📝 Iniciando geração de resumos...\n")
        # ===============================================================
        
        # Aplicar normalização preventiva
        df = _normalize_setor_df(df)
        
        if df.empty:
            print("⚠️ DataFrame de entrada está vazio")
            return pd.DataFrame(columns=["Tema", "Id", "Resumo"])
        
        print(f"📊 Processando {len(df)} prompts de setor...")
        
        # Verificar se as colunas necessárias existem
        colunas_necessarias = ['Tema', 'Prompt']
        colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]
        if colunas_faltantes:
            print(f"❌ Colunas faltantes: {colunas_faltantes}")
            return pd.DataFrame(columns=["Tema", "Id", "Resumo"])
        
        resumos = []
        for idx, row in df.iterrows():
            tema = str(row.get('Tema', f'tema_{idx}')).strip()
            prompt = str(row.get('Prompt', '')).strip()
            
            # Determinar ID - pode estar em 'Id' ou 'Ids'
            row_id = str(row.get('Ids', row.get('Id', f'id_{idx}'))).strip()
            
            if not prompt:
                print(f"⚠️ Prompt vazio para tema '{tema}', pulando...")
                continue
                
            print(f"🔄 Processando grupo {idx+1}/{len(df)} do tema '{tema}'...")

            resumo = resumir_prompt(prompt, tema, row_id)

            resumos.append({
                "Tema": tema,
                "Id": row_id,
                "Resumo": resumo
            })

            time.sleep(2)  # pausa para respeitar limites da API

        # Criar DataFrame de resultados
        if not resumos:
            print("⚠️ Nenhum resumo foi gerado")
            return pd.DataFrame(columns=["Tema", "Id", "Resumo"])
            
        df_resumo_setor = pd.DataFrame(resumos)
        print(f"✅ {len(df_resumo_setor)} resumos gerados com sucesso")

        # Limpezas no texto do resumo
        if not df_resumo_setor.empty and 'Resumo' in df_resumo_setor.columns:
            # Eliminar asteriscos do resumo final
            df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace('*', '', regex=False)

            # Eliminar linhas que começam e terminam com parênteses e que tenham a palavra "foco"
            df_resumo_setor = df_resumo_setor[~df_resumo_setor['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]

            # Eliminar do campo Resumo a expressão exata "(90 palavras)" e variações
            padroes_remover = [r'\(90 palavras\)', r'\(89 palavras\)', r'\(91 palavras\)', r'\(\d+ palavras\)']
            for padrao in padroes_remover:
                df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace(padrao, '', regex=True)
            
            df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.strip()
            
            # Para cada marca que aparece em w_marcas no campo Resumo, acrescentar um asterisco antes e outro depois
            for marca in w_marcas:
                df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace(f"(?i)\\b{re.escape(marca)}\\b", f"*{marca}*", regex=True)

        return df_resumo_setor
        
    except Exception as e:
        print(f"❌ Erro geral no processamento de resumos de setor: {e}")
        traceback.print_exc()
        # Retornar DataFrame vazio ao invés de None
        return pd.DataFrame(columns=["Tema", "Id", "Resumo"])