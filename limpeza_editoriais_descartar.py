# Rotina de limpeza do arquivo de Editoriais carregado pela API
import pandas as pd
import re

import pandas as pd

# Escolhe o primeiro nome de coluna que existir na lista de alternativas
def _choose_col(existing_cols, options):
    for o in options:
        if o in existing_cols:
            return o
    return None

# Padroniza o df de editoriais para as colunas ["Id","Titulo","Conteudo","IdVeiculo"]
def _standardize_editoriais(df_in):
    df = df_in.copy()
    cols = list(df.columns)

    # alternativas comuns que já vi nesses fluxos
    id_col        = _choose_col(cols, ['Id', 'id', 'ID'])
    titulo_col    = _choose_col(cols, ['Titulo', 'Título', 'title', 'Title'])
    conteudo_col  = _choose_col(cols, ['Conteudo', 'Conteúdo', 'Texto', 'Corpo', 'TextoCompleto', 'Body'])
    idveic_col    = _choose_col(cols, ['IdVeiculo', 'IdVeículo', 'VeiculoId', 'IdCanal', 'Id_Canal', 'VehicleId'])

    # debug útil para diagnosticar (pode deixar)
    print("💡 Mapeamento editoriais:",
          {"Id": id_col, "Titulo": titulo_col, "Conteudo": conteudo_col, "IdVeiculo": idveic_col})

    rename = {}
    selected = []
    for found, std in [(id_col, 'Id'),
                       (titulo_col, 'Titulo'),
                       (conteudo_col, 'Conteudo'),
                       (idveic_col, 'IdVeiculo')]:
        if found:
            rename[found] = std
            selected.append(found)

    # Seleciona as que existem e renomeia
    out = df[selected].rename(columns=rename).copy()

    # Garante todas as colunas padrão (preenche se faltar)
    for col in ['Id', 'Titulo', 'Conteudo', 'IdVeiculo']:
        if col not in out.columns:
            out[col] = pd.NA

    # Tipagem e limpeza mínima
    out['Id'] = pd.to_numeric(out['Id'], errors='coerce').astype('Int64')
    out = out.dropna(subset=['Id']).copy()
    out['Id'] = out['Id'].astype(int)

    # Ordem final
    return out[['Id', 'Titulo', 'Conteudo', 'IdVeiculo']]


def limpar_editoriais(editoriais_df):
    """
    Recebe o DataFrame de editoriais e devolve:
      - final_df_editorial      : padronizado com ["Id","Titulo","Conteudo","IdVeiculo"]
      - final_df_editorial_small: subset com as mesmas colunas (mantido para compatibilidade)
    """
    # proteção contra df vazio / None
    if editoriais_df is None or getattr(editoriais_df, "empty", True):
        print("⚠️ editoriais_df vazio; retornando DFs vazios.")
        empty = pd.DataFrame(columns=['Id', 'Titulo', 'Conteudo', 'IdVeiculo'])
        return empty, empty

    # padroniza nomes/formatos antes de seguir
    final_df_editorial = _standardize_editoriais(editoriais_df)

    # se você tiver alguma regra específica de filtragem de “editoriais”, aplique aqui
    # ex: final_df_editorial = final_df_editorial[ final_df_editorial['Tipo']=='Editorial' ]

    final_df_editorial_small = final_df_editorial[['Id', 'Titulo', 'Conteudo', 'IdVeiculo']].copy()
    return final_df_editorial, final_df_editorial_small


