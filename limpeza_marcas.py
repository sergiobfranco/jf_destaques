import pandas as pd
import os
import json
import re
from config import w_marcas

def limpar_marcas(final_df):
    # Remover duplicatas de IdVeiculo + Titulo
    # Convert 'DataVeiculacao' to datetime objects, coercing errors
    final_df['DataVeiculacao'] = pd.to_datetime(final_df['DataVeiculacao'], errors='coerce')

    # Sort by 'IdVeiculo', 'Titulo', and 'DataVeiculacao' in descending order
    final_df = final_df.sort_values(by=['IdVeiculo', 'Titulo', 'DataVeiculacao'], ascending=[True, True, False])

    # Remove duplicates based on 'IdVeiculo' and 'Titulo', keeping the first occurrence (which is the latest due to sorting)
    final_df = final_df.drop_duplicates(subset=['IdVeiculo', 'Titulo'], keep='first').reset_index(drop=True)


    # --- Início do ajuste ---
    print('Qtde de registros antes de desprezar lista de veículos: ', final_df.shape[0])
    # Lista de veículos a serem ignorados
    veiculos_a_ignorar = [
        #"VALOR ECONÔMICO ONLINE/SÃO PAULO",
        #"CNN BRASIL ONLINE",
        #"VALOR INVESTE",
        #"ISTOÉ DINHEIRO ONLINE/SÃO PAULO",
        #"FOLHA DE S.PAULO ONLINE/SÃO PAULO",
        #"BLOOMBERG LÍNEA/AMÉRICA LATINA",
        #"RÁDIO CBN FM 90,5/SÃO PAULO",
        #"O POVO/FORTALEZA",
        #"O POVO ONLINE/FORTALEZA",
        "nenhum"
    ]

    # Filtrar o DataFrame para remover as linhas onde a coluna 'Veiculo'
    # está presente na lista de veículos a serem ignorados.
    # Garante que a comparação seja case-insensitive e remova espaços em branco extras.
    final_df = final_df[~final_df['Veiculo'].str.strip().str.upper().isin([v.strip().upper() for v in veiculos_a_ignorar])]

    print('Qtde de registros após desprezar lista de veículos: ', final_df.shape[0])

    # --- Fim do ajuste ---

    # Substitui 'Holding' por 'J&F'

    final_df['Canais'] = final_df['Canais'].fillna('').astype(str)
    final_df['Canais'] = final_df['Canais'].str.replace(r'\bHolding\b', 'J&F', regex=True)

    # Limpeza e ajustes nos Canais

    def clean_canais(canais, w_marcas):
        """
        Remove colchetes e aspas, mantém apenas marcas em w_marcas,
        e remove vírgulas e espaços extras.
        """
        # 1. Converter para string se não for
        if not isinstance(canais, str):
            canais = str(canais)  # Converte para string

        # 2. Remover colchetes e aspas
        canais = re.sub(r"[\[\]']", "", canais)

        # 3. Manter apenas marcas em w_marcas
        marcas_validas = [marca for marca in canais.split(",") if marca.strip() in w_marcas]

        # 4. Remover vírgulas e espaços extras
        marcas_limpas = [marca.strip() for marca in marcas_validas]

        return ",".join(marcas_limpas)

    # Aplicando a função ao DataFrame
    final_df['Canais'] = final_df['Canais'].apply(lambda x: clean_canais(x, w_marcas))

    # Replicar registros com vários Canais

    # 1. Seleciona apenas as colunas de interesse
    final_df_small = final_df[['Id', 'Titulo', 'Conteudo', 'IdVeiculo', 'Canais']].copy()

    # 2. Explode os canais em listas
    final_df_small['Canais'] = final_df_small['Canais'].str.split(',')

    # 3. Replica as linhas
    final_df_small = final_df_small.explode('Canais').copy()

    # 4. Limpa espaços extras
    final_df_small['Canais'] = final_df_small['Canais'].str.strip()
    return final_df, final_df_small