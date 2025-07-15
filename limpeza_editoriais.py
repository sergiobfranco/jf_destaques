# Rotina de limpeza do arquivo de Editoriais carregado pela API
import pandas as pd
import re

def limpar_editoriais(final_df_editorial):

    # Criar o DataFrame 'final_df_small' após a filtragem
    final_df_editorial_small = final_df_editorial[['Id', 'Titulo', 'Conteudo', 'IdVeiculo']].copy()

    return final_df_editorial, final_df_editorial_small

