import requests
import pandas as pd
import os
import configparser
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

from config import DEEPSEEK_API_URL

def avaliar_relevancia(df):
    PROMPT_CHARACTER_LIMIT = 30000

    #arq_api = 'api/Favoritos_Marcas_small.xlsx'
    #darq_relevancia_irrelevantes = 'api/Favoritos_Marcas_Irrelevantes.xlsx' # Esta variável não será mais usada para salvar o arquivo
    #arq_prompts = 'marca_setor/Prompts_Resumo_Noticias_DBSCAN.xlsx'

    api_key = obter_chave_deepseek()

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Carregamento inicial
    #df = pd.read_excel(arq_api)
    df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')
    marcas = df['Canais'].dropna().unique()

    # Função para avaliar se a marca é relevante na notícia
    def avaliar_relevancia_marca(marca, texto):
        prompt = (
            f"Avalie a relevância da marca \"{marca}\" na seguinte notícia.\n\n"
            "A marca deve ser considerada relevante quando influencia ou é influenciada pelos fatos descritos no texto, mesmo que de forma indireta ou moderada. "
            "Caso contrário, se a marca for apenas citada superficialmente, sem vínculo com os eventos principais, considere irrelevante.\n\n"
            "Responda apenas com 'True' (se for relevante) ou 'False' (se não for relevante).\n\n"
            f"Texto:\n{texto}"
        )

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 10
        }

        try:
            print(f"Enviando requisição ao DeepSeek para avaliar a marca '{marca}'...")
            response = requests.post(DEEPSEEK_API_URL, headers=HEADERS, json=data)
            response.raise_for_status()
            resposta = response.json()["choices"][0]["message"]["content"].strip()
            print(f"Resposta do DeepSeek: {resposta}")
            return resposta.lower().startswith("true")
        except Exception as e:
            print(f"Erro ao avaliar relevância: {e}")
            return True  # Em caso de erro, assume como relevante para não perder

    # Avalia relevância se ainda não tiver sido feito
    if 'RelevanciaMarca' not in df.columns or df['RelevanciaMarca'].isnull().all():
        print("Avaliando relevância da marca nas notícias...")
        df['RelevanciaMarca'] = df.apply(lambda row: avaliar_relevancia_marca(row['Canais'], row['TextoCompleto']), axis=1)

        # --- Início do ajuste para remover duplicatas relevantes ---
        # Define a ordem de prioridade das marcas
        # Removed duplicate 'Eldorado' from the list
        marca_order = ['JBS', 'J&F', 'PicPay', 'Eldorado', 'Joesley Batista', 'Wesley Batista', 'Banco Original']

        # Cria uma coluna temporária para ordenação personalizada
        df['Marca_Order'] = pd.Categorical(df['Canais'], categories=marca_order, ordered=True)

        # Filtra apenas as notícias relevantes (RelevanciaMarca == True) para aplicar a lógica de desduplicação
        df_relevantes = df[df['RelevanciaMarca'] == True].copy()

        # Ordena por Id e pela ordem de prioridade das marcas
        # Para IDs duplicados, a linha com a marca de maior prioridade (menor valor na categoria) virá primeiro
        df_relevantes_sorted = df_relevantes.sort_values(by=['Id', 'Marca_Order'], ascending=[True, True])

        # Remove duplicatas de Id, mantendo a primeira ocorrência (que será a de maior prioridade devido à ordenação)
        df_relevantes_deduplicadas = df_relevantes_sorted.drop_duplicates(subset='Id', keep='first')

        # Remove a coluna temporária de ordenação
        df_relevantes_deduplicadas = df_relevantes_deduplicadas.drop(columns=['Marca_Order'])

        # Separa as notícias irrelevantes do DataFrame original
        df_irrelevantes = df[df['RelevanciaMarca'] == False].copy()

        # Remove a coluna temporária de ordenação das irrelevantes também
        df_irrelevantes = df_irrelevantes.drop(columns=['Marca_Order'])


        # Concatena as notícias relevantes deduplicadas com as irrelevantes
        # A ordem das linhas não é garantida após a concatenação, mas as linhas corretas foram mantidas.
        # Se a ordem original for importante, pode ser necessário um passo adicional para reordenar.
        df_final_relevancia = pd.concat([df_relevantes_deduplicadas, df_irrelevantes], ignore_index=True)

        # --- NOVO PASSO: Remover notícias irrelevantes de df_final_relevancia ---
        print("Removendo notícias irrelevantes de df_final_relevancia...")
        df_final_relevancia = df_final_relevancia[df_final_relevancia['RelevanciaMarca'] == True].copy()
        print(f"df_final_relevancia agora contém {len(df_final_relevancia)} notícias relevantes.")
        # --- FIM NOVO PASSO ---


        # Salva o DataFrame final (agora apenas relevantes) no arquivo de relevância
        #df_final_relevancia.to_excel("api/Favoritos_Marcas_Relevancia.xlsx", index=False)
        #print("Arquivo api/Favoritos_Marcas_Relevancia.xlsx salvo (contém apenas notícias relevantes).")

        # --- Novo: Remover registros de final_df_small_marca que não estão em df_final_relevancia (Id e Canais) ---
        # Carregar final_df_small_marca para processamento
        #final_df_small_marca = pd.read_excel(arq_api)
        final_df_small_marca = df

        # Criar um conjunto de tuplas (Id, Canais) das notícias que devem ser MANTIDAS (usando o df_final_relevancia já filtrado)
        ids_canais_to_keep = set(zip(df_final_relevancia['Id'], df_final_relevancia['Canais']))

        # Filtrar final_df_small_marca para manter apenas as linhas cujos (Id, Canais) estão no conjunto
        # Ensure 'Canais' is treated as string in both DFs for consistent comparison
        final_df_small_marca['Canais'] = final_df_small_marca['Canais'].astype(str)
        df_final_relevancia['Canais'] = df_final_relevancia['Canais'].astype(str)

        ids_canais_to_keep = set(zip(df_final_relevancia['Id'], df_final_relevancia['Canais']))

        # Apply the filter
        final_df_small_marca_processed = final_df_small_marca[
            final_df_small_marca.apply(lambda row: (row['Id'], row['Canais']) in ids_canais_to_keep, axis=1)
        ].copy()

        return final_df_small_marca_processed, df_irrelevantes

        # Sobrescrever o arquivo Favoritos_Marcas_small.xlsx
        #final_df_small_marca_processed.to_excel(arq_api, index=False)
        #print(f"Arquivo {arq_api} sobrescrito após remoção de registros que não foram considerados relevantes/prioritários.")

        # --- Fim do novo ajuste ---


    else:
        print("Coluna RelevanciaMarca já presente.")
        # Se a coluna já existe, mas o usuário quer aplicar a desduplicação,
        # você pode adicionar a lógica de desduplicação aqui também,
        # lendo o arquivo existente e re-salvando após a desduplicação.
        # Por simplicidade nesta resposta, apenas imprimimos a mensagem.
        # Para um comportamento mais robusto, a lógica de desduplicação
        # poderia ser aplicada sempre, ou ter uma flag para controlá-la.
        # Como a coluna RelevanciaMarca já existe, vamos carregar o df
        # e aplicar a lógica de desduplicação para garantir que o arquivo
        # de relevância esteja correto para as próximas etapas.

        print("Aplicando desduplicação em notícias relevantes do arquivo existente...")
        # Removed duplicate 'Eldorado' from the list
        marca_order = ['JBS', 'J&F', 'PicPay', 'Eldorado', 'Joesley Batista', 'Wesley Batista', 'Banco Original']
        df['Marca_Order'] = pd.Categorical(df['Canais'], categories=marca_order, ordered=True)
        df_relevantes = df[df['RelevanciaMarca'] == True].copy()
        df_relevantes_sorted = df_relevantes.sort_values(by=['Id', 'Marca_Order'], ascending=[True, True])
        df_relevantes_deduplicadas = df_relevantes_sorted.drop_duplicates(subset='Id', keep='first')
        df_relevantes_deduplicadas = df_relevantes_deduplicadas.drop(columns=['Marca_Order'])

        df_irrelevantes = df[df['RelevanciaMarca'] == False].copy()
        df_irrelevantes = df_irrelevantes.drop(columns=['Marca_Order']) # Remove se existia antes ou foi criada

        df_final_relevancia = pd.concat([df_relevantes_deduplicadas, df_irrelevantes], ignore_index=True)

        # --- NOVO PASSO: Remover notícias irrelevantes de df_final_relevancia (no bloco else) ---
        print("Removendo notícias irrelevantes de df_final_relevancia (no bloco else)...")
        df_final_relevancia = df_final_relevancia[df_final_relevancia['RelevanciaMarca'] == True].copy()
        print(f"df_final_relevancia agora contém {len(df_final_relevancia)} notícias relevantes (no bloco else).")
        # --- FIM NOVO PASSO ---

        df_final_relevancia.to_excel("api/Favoritos_Marcas_Relevancia.xlsx", index=False)
        print("Arquivo api/Favoritos_Marcas_Relevancia.xlsx re-salvo após desduplicação (contém apenas notícias relevantes).")

        # --- Novo: Remover registros de final_df_small_marca que não estão em df_final_relevancia (Id e Canais) (caso a coluna já existisse) ---
        # Carregar final_df_small_marca para processamento
        #final_df_small_marca = pd.read_excel(arq_api)
        final_df_small_marca = df

        # Criar um conjunto de tuplas (Id, Canais) das notícias que devem ser MANTIDAS (usando o df_final_relevancia já filtrado)
        # Ensure 'Canais' is treated as string in both DFs for consistent comparison
        final_df_small_marca['Canais'] = final_df_small_marca['Canais'].astype(str)
        df_final_relevancia['Canais'] = df_final_relevancia['Canais'].astype(str)

        ids_canais_to_keep = set(zip(df_final_relevancia['Id'], df_final_relevancia['Canais']))

        # Apply the filter
        final_df_small_marca_processed = final_df_small_marca[
            final_df_small_marca.apply(lambda row: (row['Id'], row['Canais']) in ids_canais_to_keep, axis=1)
        ].copy()

        # Sobrescrever o arquivo Favoritos_Marcas_small.xlsx
        #final_df_small_marca_processed.to_excel(arq_api, index=False)
        print(f"Arquivo {arq_api} sobrescrito após remoção de registros que não foram considerados relevantes/prioritários (coluna RelevanciaMarca já existia).")
        
        return final_df_small_marca_processed
        # --- Fim do novo ajuste (caso a coluna já existisse) ---


    # --- Fim do ajuste para remover duplicatas relevantes ---
