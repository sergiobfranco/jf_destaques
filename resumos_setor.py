# Rotina para gerar os resumos de Setor pelo DeepSeek

import pandas as pd
import requests
import time
import configparser
import os
import traceback

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



def gerar_resumos_setor(df):
    api_key = obter_chave_deepseek()

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }    
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

    # Eliminar asteriscos do resumo final
    df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace('*', '', regex=False)

    # Eliminar linhas que começam e terminam com parênteses e que tenham a palavra "foco"
    df_resumo_setor = df_resumo_setor[~df_resumo_setor['Resumo'].str.contains(r'^\(.*foco.*\)$', regex=True)]

    # Eliminar do campo Resumo a expressão exata "(90 palavras)"
    df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace(r'\(90 palavras\)', '', regex=True)
    df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.strip()
    
    # Para cada marca que aparece em w_marcas no campo Resumo, acrescentar um asterisco antes e outro depois
    for marca in w_marcas:
        df_resumo_setor['Resumo'] = df_resumo_setor['Resumo'].str.replace(f"(?i)\\b{marca}\\b", f"*{marca}*", regex=True)    

    return df_resumo_setor
