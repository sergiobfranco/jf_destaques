# Etapa 2: Resumo de até 60 palavras, agrupamento semântico e geração de resumos finais com refinamento por subtemas
# Esta versão foi gerada em 14/08/25 melhorando o retorno dos resumos com parser robusto + formato JSON

import pandas as pd
import os
import requests
import re
import configparser
import traceback
import datetime
import time
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



def agrupar_noticias_por_similaridade(arq_textos):
    api_key = obter_chave_deepseek()

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    LIMITE_CARACTERES_GRUPO = 12000

    # ================= NORMALIZAÇÃO CRÍTICA (NOVO) =================
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
            # coagir para Int64, remover NaN e voltar para string
            try:
                df['Id'] = pd.to_numeric(df['Id'], errors='coerce').astype('Int64')
                df = df.dropna(subset=['Id']).copy()
                df['Id'] = df['Id'].astype(int).astype(str)
            except Exception:
                # fallback: garantir string mesmo assim
                df['Id'] = df['Id'].astype(str)

        return df
    # ===============================================================

    def gerar_resumo_60(texto, id_):
        for tentativa in range(3):
            try:
                print(f"📝 Gerando resumo curto para notícia ID: {id_}...")
                prompt = "Resuma o conteúdo a seguir em até 60 palavras.\n\n" + texto
                data = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 120
                }
                r = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data, timeout=45)
                r.raise_for_status()
                out = r.json()["choices"][0]["message"]["content"].strip()
                if out:
                    return out
            except Exception as e:
                print(f"Resumo60 falhou (tentativa {tentativa+1}) ID {id_}: {e}")
                time.sleep(1 + tentativa)
        # fallback barato
        titulo_e_conteudo = texto[:2000]
        return titulo_e_conteudo[:260]

    def gerar_resumo_60_original(texto, id_):
        print(f"📝 Gerando resumo curto para notícia ID: {id_}...")
        prompt = "Resuma o conteúdo a seguir em até 60 palavras.\n\n" + texto
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 120
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Erro ao gerar resumo curto para ID {id_}: {e}")
            return ""

    def agrupar_por_similaridade(resumos):
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
            return grupos
        except Exception as e:
            print(f"Erro ao agrupar resumos: {e}")
            return list(range(1, N+1))

    def agrupar_por_similaridade_original(resumos):
        # (mantido igual; não usado por padrão)
        ...

    def gerar_resumo_120(textos, marca):
        corpo = "\n--- NOTÍCIA ---\n".join(textos)
        prompt = f"Gere um resumo único de até 120 palavras para as notícias a seguir sobre a marca '{marca}', destacando os fatos mais importantes:\n\n{corpo}"
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
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
            return texto.strip()
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
        # --------- AQUI é onde antes você fazia df = arq_textos; df['Id'] = df['Id'].astype(str) ---------
        df = _normalize_df(arq_textos)  # (substitui as duas linhas antigas)  :contentReference[oaicite:5]{index=5}
        df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

        # Esta linha era onde estourava 'unhashable type: list' quando Canais vinha como lista
        todas_marcas = df['Canais'].dropna().unique().tolist()  # agora são strings normalizadas  :contentReference[oaicite:6]{index=6}
        resultados = []

        for marca in todas_marcas:
            print(f"\n🔍 Processando marca: {marca}")
            df_marca = df[df['Canais'] == marca].copy().reset_index(drop=True)

            resumos = [gerar_resumo_60(row['TextoCompleto'], row['Id']) for _, row in df_marca.iterrows()]
            df_marca['Resumo60'] = resumos

            grupos = agrupar_por_similaridade(resumos)
            df_marca['GrupoID'] = grupos

            for grupo_id, df_grupo in df_marca.groupby('GrupoID'):
                textos = df_grupo['TextoCompleto'].tolist()
                ids = df_grupo['Id'].astype(str).tolist()
                resumo_final = gerar_resumo_consolidado_por_chunks(textos, marca)
                resultados.append({
                    "Marca": marca,
                    "GrupoID": f"{marca}_G{grupo_id}",
                    "QtdNoticias": len(ids),
                    "Ids": ','.join(ids),  # mantém string csv — o relatório depende disso :contentReference[oaicite:7]{index=7}
                    "Resumo": resumo_final
                })

        # Garante colunas mesmo se não houver resultados (evita KeyError nas transformações seguintes)
        df_final = pd.DataFrame(resultados, columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])

        # ---------- Short URLs para o merge no main/relatórios ----------
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

        # ---------- Limpezas no texto do resumo (só se houver linhas) ----------
        if not df_final.empty and 'Resumo' in df_final.columns:
            df_final['Resumo'] = df_final['Resumo'].astype(str).str.replace('*', '', regex=False)
            df_final = df_final[~df_final['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]
            for marca in w_marcas:
                df_final['Resumo'] = df_final['Resumo'].str.replace(f"(?i)\\b{re.escape(marca)}\\b", f"*{marca}*", regex=True)

        return df_final

    except Exception as e:
        import traceback as _tb
        print(f"Erro geral no processamento: {e}")
        print(_tb.format_exc(limit=1))
        # >>> NÃO retornar None: devolve DF vazio com o cabeçalho esperado
        return pd.DataFrame(columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])  # :contentReference[oaicite:8]{index=8}

