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
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Você é um jornalista profissional especializado em resumir notícias."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.7
        }

        # Implementar retry com backoff
        for tentativa in range(3):
            try:
                print(f"🔄 Tentativa {tentativa + 1} para tema: {tema} (ID: {row_id})")
                response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=payload, timeout=60)
                response.raise_for_status()
                resultado = response.json()['choices'][0]['message']['content']
                
                # Verificar se o resultado não está vazio
                if resultado and resultado.strip():
                    return resultado.strip()
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