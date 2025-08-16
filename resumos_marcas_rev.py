import pandas as pd
import os
import requests
import re
import configparser
import traceback
from dotenv import load_dotenv
from config import DEEPSEEK_API_URL, w_marcas

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

def agrupar_noticias_por_similaridade(arq_textos):
    api_key = obter_chave_deepseek()
    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    LIMITE_CARACTERES_GRUPO = 12000

    def gerar_resumo_60(texto, id_):
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
        print(f"🔗 Enviando {len(resumos)} resumos para agrupamento semântico via DeepSeek...")
        prompt = (
            "Agrupe os resumos abaixo por similaridade de assunto. "
            "Considere similares notícias com títulos ou conteúdos quase idênticos, "
            "mesmo que haja pequenas diferenças de redação ou detalhe. "
            "Agrupe sempre que o foco central e contexto forem os mesmos. "
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
            linhas = texto.split('\n')
            linhas_filtradas = []
            for linha in linhas:
                linha_strip = linha.strip()
                if re.match(r'^\*\*\s*resumo.*\*\*\s*$', linha_strip, re.IGNORECASE):
                    print(f"🗑️ Removendo linha: {linha_strip}")
                    continue
                linhas_filtradas.append(linha)
            texto = '\n'.join(linhas_filtradas)
            texto = re.sub(r"^\*\*[^*]*\*\*\s*", "", texto, flags=re.IGNORECASE | re.MULTILINE)
            texto = re.sub(r"\*\(Exatamente\s*120\s*palavras\)\*|\*\(120\s*palavras\)\*", "", texto, flags=re.IGNORECASE)
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
        if df is None or df.empty:
            print("⚠️ Nenhuma notícia recebida. Retornando DataFrame vazio com estrutura padrão.")
            return pd.DataFrame(columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])

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
                    "Ids": ','.join(ids),
                    "Resumo": resumo_final
                })

        df_final = pd.DataFrame(resultados)
        import pyshorteners
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
        df[['Id', 'Canais', 'ShortURL']].to_excel('dados/api/shorturls_por_id.xlsx', index=False)
        print("✅ Arquivo shorturls_por_id.xlsx salvo com ShortURLs.")
        df_final['Resumo'] = df_final['Resumo'].str.replace('*', '', regex=False)
        df_final = df_final[~df_final['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]
        for marca in w_marcas:
            df_final['Resumo'] = df_final['Resumo'].str.replace(f"(?i)\\b{marca}\\b", f"*{marca}*", regex=True)
        return df_final

    except Exception as e:
        print(f"❌ Erro geral no processamento de agrupar_noticias_por_similaridade: {e}")
        traceback.print_exc()
        return pd.DataFrame(columns=["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"])
