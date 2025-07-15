# Rotina de limpeza do arquivo de Specials carregado pela API

import pandas as pd

def limpar_specials(final_df_SPECIALS):

    # Converter a coluna 'Titulo' para string e preencher NaNs com vazio para evitar erros
    final_df_SPECIALS['Titulo'] = final_df_SPECIALS['Titulo'].astype(str).fillna('')

    # Criar o DataFrame 'final_df_small' após a filtragem
    final_df_SPECIALS_small = final_df_SPECIALS[['Id', 'Canais']].copy()

    return final_df_SPECIALS, final_df_SPECIALS_small

