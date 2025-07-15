# Rotina para gerar os resumos de Setor pelo DeepSeek

import pandas as pd
import requests
import time

from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY

HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def gerar_resumos_setor(df):
    # 2. Carrega prompts gerados
    #df = pd.read_excel(arq_prompts_setor)

    # 3. Função para chamar a API
    def resumir_prompt(prompt_text):
        payload = {
    #        "model": "deepseek/deepseek-chat",
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Você é um jornalista profissional especializado em resumir notícias."},
                {"role": "user", "content": prompt_text}
            ],
            "temperature": 0.7
        }

        try:
            #print(payload)
            response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Erro: {e}"

    # 4. Processa todos os prompts
    resumos = []
    for idx, row in df.iterrows():
        print(f"Processando grupo {idx+1}/{len(df)} do tema {row['Tema']}...")

        prompt = row['Prompt']
        resumo = resumir_prompt(prompt)

        resumos.append({
            "Tema": row['Tema'],
            #"GrupoID": row['GrupoID'],
            #"QtdNoticias": row['QtdNoticias'],
            "Id": row['Ids'],
            "Resumo": resumo
        })

        time.sleep(2)  # pausa para respeitar limites da API

    # 5. Salva resultados
    df_resumo_setor = pd.DataFrame(resumos)

    #df_resumo_setor.to_excel(arq_results_setor, index=False)
    #print("Arquivo salvo: ", arq_results_setor)

    return df_resumo_setor
