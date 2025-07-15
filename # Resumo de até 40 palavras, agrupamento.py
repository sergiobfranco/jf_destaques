# Resumo de até 40 palavras, agrupamento semântico e geração de resumos finais com refinamento por subtemas

import pandas as pd
import os
import requests
import re

from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
}

def gerar_resumo_40(texto, id_):
    print(f"📝 Gerando resumo curto para notícia ID: {id_}...")
    prompt = "Resuma o conteúdo a seguir em até 40 palavras.\n\n" + texto
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 100
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
        texto = re.sub(r"^\*\*?Resumo.*?\*\*?\s*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\*\(160 palavras\)\*|\*\(Exatamente 160 palavras\)\*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\n{2,}", "\n", texto).strip()
        return texto
    except Exception as e:
        print(f"Erro ao gerar resumo final: {e}")
        return ""

def reavaliar_grupo(grupo_df):
    resumos = grupo_df['Resumo40'].tolist()
    ids = grupo_df['Id'].tolist()
    subgrupos = agrupar_por_similaridade(resumos)
    grupo_df = grupo_df.copy()
    grupo_df['SubGrupoID'] = subgrupos
    return grupo_df

def agrupar_noticias_por_similaridade(df_small):
    try:
        df = df_small
        df['Id'] = df['Id'].astype(str)
        df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

        lista_resumos = []
        for _, row in df.iterrows():
            resumo = gerar_resumo_40(row['TextoCompleto'], row['Id'])
            lista_resumos.append({"Id": row['Id'], "Marca": row['Canais'], "TextoCompleto": row['TextoCompleto'], "Resumo40": resumo})

        df_resumos = pd.DataFrame(lista_resumos)
        grupos_iniciais = agrupar_por_similaridade(df_resumos['Resumo40'].tolist())
        df_resumos['GrupoID'] = grupos_iniciais

        refinado = []
        for (marca, grupo), grupo_df in df_resumos.groupby(['Marca', 'GrupoID']):
            if len(grupo_df) > 1:
                print(f"🔍 Reavaliando grupo {grupo} da marca {marca}...")
                grupo_df = reavaliar_grupo(grupo_df)
            else:
                grupo_df['SubGrupoID'] = 0
            refinado.append(grupo_df)

        df_refinado = pd.concat(refinado).reset_index(drop=True)

        resultados = []
        for (marca, grupo, subgrupo), df_sub in df_refinado.groupby(['Marca', 'GrupoID', 'SubGrupoID']):
            textos = df_sub['TextoCompleto'].tolist()
            ids = df_sub['Id'].tolist()
            resumo_final = gerar_resumo_160(textos, marca)
            resultados.append({
                "Marca": marca,
                "GrupoID": f"{marca}_G{grupo}_S{subgrupo}",
                "QtdNoticias": len(ids),
                "Ids": ','.join(ids),
                "Resumo": resumo_final
            })

        df_final = pd.DataFrame(resultados)

        return df_final

    except Exception as e:
        print(f"Erro geral no processamento: {e}")
