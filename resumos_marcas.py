# Etapa 2: Resumo de até 60 palavras, agrupamento semântico e geração de resumos finais com refinamento por subtemas

import pandas as pd
import os
import requests
import re

from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY, w_marcas

HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def agrupar_noticias_por_similaridade(arq_textos):

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

    def gerar_resumo_160(textos, marca):
        corpo = "\n--- NOTÍCIA ---\n".join(textos)
        prompt = f"Gere um resumo único de até 160 palavras para as notícias a seguir sobre a marca '{marca}', destacando os fatos mais importantes:\n\n{corpo}"
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

            # Remover sufixos do tipo "*160 palavras*" ou "*Exatamente 160 palavras*"
            texto = re.sub(r"\*\(Exatamente\s*160\s*palavras\)\*|\*\(160\s*palavras\)\*", "", texto, flags=re.IGNORECASE)

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

        resumos_intermediarios = [gerar_resumo_160(grupo, marca) for grupo in grupos]
        if len(resumos_intermediarios) == 1:
            return resumos_intermediarios[0]
        else:
            print("🔗 Consolidando subgrupos em resumo final...")
            return gerar_resumo_160(resumos_intermediarios, marca)

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
