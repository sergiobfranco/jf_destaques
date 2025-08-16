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
        from sklearn.feature_extraction.text import TfidfVectorizer
        from collections import Counter
        titulo_e_conteudo = texto[:2000]
        # extraia 6-10 top termos rápidos – ou simplesmente devolva o título
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
            f"Retorne **somente** uma linha em JSON, sem comentários nem markdown, exatamente assim:\n"
            f'{{"groups":[g1,...,g{N}]}}\n'
            f"O array deve ter exatamente {N} inteiros (>=1). Nada além do JSON.\n\n"
        )
        for i, r in enumerate(resumos, 1):
            prompt += f"Resumo {i}: {r}\n"

        data = {"model": "deepseek-chat","messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":200}
        try:
            resp = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data); resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

            # 1) Tente JSON direto
            m = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    grupos = obj.get("groups", [])
                except Exception:
                    grupos = []
            else:
                grupos = []

            # 2) Se falhar, extraia primeira sequência de inteiros do tamanho N
            if not grupos:
                nums = list(map(int, re.findall(r'\d+', content)))
                grupos = nums[:N]

            # 3) Normalizações
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
        print(f"🔗 Enviando {len(resumos)} resumos para agrupamento semântico via DeepSeek...")
        prompt = (
            "Agrupe os resumos abaixo por similaridade de assunto. "
            "Considere como similar não apenas assuntos idênticos, mas também aqueles com forte relação temática, como diferentes aspectos de um mesmo setor, empresa ou impacto.\n"
            "Retorne uma única linha com os números dos grupos separados por vírgula, na mesma ordem dos resumos.\n"
            "Exemplo: 1,1,2,2,3\n\n"
        )
        for i, resumo in enumerate(resumos):
            prompt += f"Resumo {i+1}: {resumo}\n"
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 400
        }
        try:
            response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            print("📤 Resposta bruta do agrupamento:")
            print(content)
            linha_grupos = next((l for l in content.splitlines() if re.match(r"^\d+(,\d+)*$", l.strip())), "")
            if not linha_grupos:
                print("⚠️ Nenhuma linha de grupo reconhecida. Conteúdo retornado:")
                for linha in content.splitlines():
                    print(f"> {linha}")
            else:
                print(f"✅ Linha de grupos detectada: {linha_grupos}")
            grupos = [int(g) for g in linha_grupos.strip().split(",")] if linha_grupos else list(range(len(resumos)))
            if len(grupos) != len(resumos):
                print("⚠️ Número de grupos não bate. Atribuindo grupos únicos...")
                return list(range(len(resumos)))
            return grupos
        except Exception as e:
            print(f"Erro ao agrupar resumos: {e}")
            return list(range(len(resumos)))

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

            # Remover linhas que começam com "** Resumo" e terminam com "** "
            # Isso remove linhas inteiras que seguem esse padrão
            linhas = texto.split('\n')
            linhas_filtradas = []
            
            for linha in linhas:
                linha_strip = linha.strip()
                # Verifica se a linha começa com "** Resumo" (case insensitive) e termina com "** "
                if re.match(r'^\*\*\s*resumo.*\*\*\s*$', linha_strip, re.IGNORECASE):
                    print(f"🗑️ Removendo linha: {linha_strip}")
                    continue
                linhas_filtradas.append(linha)
            
            texto = '\n'.join(linhas_filtradas)

            # Remover outros prefixos do tipo "** ... **" no início do texto (versão mais específica)
            texto = re.sub(r"^\*\*[^*]*\*\*\s*", "", texto, flags=re.IGNORECASE | re.MULTILINE)

            # Remover sufixos do tipo "*120 palavras*" ou "*Exatamente 120 palavras*"
            texto = re.sub(r"\*\(Exatamente\s*120\s*palavras\)\*|\*\(120\s*palavras\)\*", "", texto, flags=re.IGNORECASE)

            # Remover múltiplas linhas em branco
            texto = re.sub(r"(\n\s*)+", "\n", texto.strip())

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
        df = arq_textos
        df['Id'] = df['Id'].astype(str)
        df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

        todas_marcas = df['Canais'].dropna().unique()
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
                    "Ids": ','.join(ids),  # <-- manter sempre como string separada por vírgula
                    "Resumo": resumo_final
                })

        df_final = pd.DataFrame(resultados)

        import pyshorteners  # certifique-se de ter instalado: pip install pyshorteners

        s = pyshorteners.Shortener()
        short_urls = []

        print("🔗 Gerando ShortURLs para todas as notícias...")

        for _, row in df.iterrows():
            url = row.get('UrlVisualizacao', '')
            try:
                short_url = s.tinyurl.short(url) if url else ''
            except Exception as e:
                print(f"⚠️ Erro ao encurtar URL para ID {row['Id']}: {e}")
                short_url = url
            short_urls.append(short_url)

        df['ShortURL'] = short_urls

        # Salve um CSV ou Excel com os campos necessários para o relatorio_preliminar.py
        df[['Id', 'Canais', 'ShortURL']].to_excel('dados/api/shorturls_por_id.xlsx', index=False)
        print("✅ Arquivo shorturls_por_id.xlsx salvo com ShortURLs.")

        # Eliminar asteriscos do resumo final
        df_final['Resumo'] = df_final['Resumo'].str.replace('*', '', regex=False)

        # Eliminar linhas que começam e terminam com parênteses e que tenham a palavra "foco"
        df_final = df_final[~df_final['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]

        # Para cada marca que aparece em w_marcas no campo Resumo, acrescentar um asterisco antes e outro depois
        for marca in w_marcas:
            df_final['Resumo'] = df_final['Resumo'].str.replace(f"(?i)\\b{marca}\\b", f"*{marca}*", regex=True) 

        return df_final

    except Exception as e:
        print(f"Erro geral no processamento: {e}")
        return None
