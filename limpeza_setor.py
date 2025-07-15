# Rotina que faz a limpeza do arquivo de SETOR carregado pela API

import pandas as pd
import re
from config import marcas_a_ignorar

def limpar_setor(final_df_setor):
    # --- Added code to remove duplicates based on IdVeiculo + Titulo + DataVeiculacao ---
    # Remover duplicatas de IdVeiculo + Titulo
    # Convert 'DataVeiculacao' to datetime objects, coercing errors
    final_df_setor['DataVeiculacao'] = pd.to_datetime(final_df_setor['DataVeiculacao'], errors='coerce')

    # Sort by 'IdVeiculo', 'Titulo', and 'DataVeiculacao' in descending order
    final_df_setor = final_df_setor.sort_values(by=['IdVeiculo', 'Titulo', 'DataVeiculacao'], ascending=[True, True, False])

    # Remove duplicates based on 'IdVeiculo' and 'Titulo', keeping the first occurrence (which is the latest due to sorting)
    final_df_setor = final_df_setor.drop_duplicates(subset=['IdVeiculo', 'Titulo'], keep='first').reset_index(drop=True)
    # --- End of added code ---

    # Variável com os títulos a ignorar
    titulos_a_ignorar = ["capa", "Alice Ferraz", "Curtas", "Editorial", "Expediente", "horóscopo", \
                        "mensagens", "MIRIAM LEITÃO", "MÔNICA BERGAMO", "multitela", "Obituário", \
                        "Outro canal", "Painel", "Play", "sesc", "cartas de leitores", "coluna de broadcast", \
                        "coluna do estadão", "frase do dia"]

    # Converter a coluna 'Titulo' para string e preencher NaNs com vazio para evitar erros
    final_df_setor['Titulo'] = final_df_setor['Titulo'].astype(str).fillna('')

    # Filtrar registros cujo Titulo começa com os termos a ignorar (comparação em minúsculas)
    # Criar uma máscara booleana para as linhas a serem mantidas
    mask = ~final_df_setor['Titulo'].str.lower().str.startswith(tuple(t.lower() for t in titulos_a_ignorar))

    # Aplicar a máscara para remover as linhas indesejadas
    final_df_setor = final_df_setor[mask].copy()

    # --- Added code to remove illegal characters ---
    # Function to remove illegal characters
    def remove_illegal_chars(text):
        if isinstance(text, str):
            # Remove characters not allowed in XML (and thus often in Excel)
            # This regex removes characters in the range U+0000 to U+0008, U+000B, U+000C, U+000E to U+001F
            illegal_chars = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
            return illegal_chars.sub('', text)
        return text

    # Apply the function to the 'Conteudo' column
    final_df_setor['Conteudo'] = final_df_setor['Conteudo'].apply(remove_illegal_chars)
    # --- End of added code ---

    #final_df_setor.to_excel(arq_api_original_setor_inter, index=False)

    #print("Arquivo Excel salvo como ", arq_api_original_setor)

    # ↓↓↓↓↓↓↓↓↓↓ INÍCIO DO TRECHO PARA DESPREZAR REGISTROS DO ARQUIVO DE SETOR ↓↓↓↓↓↓↓↓↓↓↓↓↓↓

    # Assuming final_df_setor and w_marcas are already defined in your environment

    # 1. Eliminar registros com Secao indesejada (em minúsculas)
    secoes_a_ignorar = ["esportes", "cotidiano", "folha corrida", "rio", "saúde", "opinião", "na web", \
                        "classificados", "cultura", "ilustrada"]

    # Create a list of the lowercased and stripped versions of the sections to ignore
    secoes_a_ignorar_cleaned = [s.strip().lower() for s in secoes_a_ignorar]

    # Clean the 'Secao' column by stripping whitespace and converting to lowercase
    final_df_setor['Secao_cleaned'] = final_df_setor['Secao'].astype(str).str.strip().str.lower()

    # Now apply the filter using the cleaned column and the cleaned list of sections to ignore
    final_df_setor_filtered = final_df_setor[
        ~final_df_setor['Secao_cleaned'].isin(secoes_a_ignorar_cleaned)
    ].copy()

    # You can drop the temporary 'Secao_cleaned' column if you don't need it later
    final_df_setor_filtered = final_df_setor_filtered.drop(columns=['Secao_cleaned'])

    # 2. Eliminar registros cujo campo CanaisCommodities atenda às novas condições
    # Condição para CanaisCommodities conter "Obituários"
    condition_contains_obituarios = final_df_setor_filtered['CanaisCommodities'].astype(str).str.lower().str.contains('obituários', na=False)

    # Combinar as condições de exclusão: (contém Obituários)
    mask_exclude_canais = condition_contains_obituarios

    # Filtrar o DataFrame para manter as linhas que NÃO atendem às condições de exclusão
    final_df_setor_filtered = final_df_setor_filtered[~mask_exclude_canais].copy()

    # 3. Eliminar registros cujo campo Conteudo contiver qualquer um dos termos constantes da variável marcas_a_ignorar (comparar em minúsculas)
    # Criar um padrão regex para buscar qualquer uma das palavras em marcas_a_ignorar, com boundary words
    marcas_a_ignorar_lower = [marca.lower() for marca in marcas_a_ignorar]
    pattern_marcas_a_ignorar = r'\b(' + '|'.join(re.escape(marca) for marca in marcas_a_ignorar_lower) + r')\b'

    # --- Modified this line to use the already cleaned 'Conteudo' column ---
    final_df_setor_filtered = final_df_setor_filtered[
        ~final_df_setor_filtered['Conteudo'].str.lower().str.contains(pattern_marcas_a_ignorar, na=False)
    ].copy()
    # --- End of modification ---

    # 4. Eliminar registros onde no campo Conteudo tenha, numa mesma linha,
    # que comece com "leia mais" ou "leia também", e em outro lugar qualquer
    # da mesma linha, contiver qualquer um dos termos constantes da variável marcas_a_ignorar (comparar em minúsculas)

    # Primeiro, lidar com valores NaN na coluna 'Conteudo'
    final_df_setor_filtered['Conteudo'] = final_df_setor_filtered['Conteudo'].fillna('')

    # Função para verificar a condição combinada em cada linha
    def check_leia_mais_and_marcas_a_ignorar(content, marcas_a_ignorar):
        content_lower = content.lower()
        starts_with_leia = content_lower.strip().startswith("leia mais") or content_lower.strip().startswith("leia também")

        # Check if any of the marcas_a_ignorar are present in the lowercased content
        marca_present = any(re.search(r'\b' + re.escape(marca.lower()) + r'\b', content_lower) for marca in marcas_a_ignorar)

        return starts_with_leia and marca_present

    # Aplicar a função para criar uma máscara booleana
    # --- Modified this line to use the already cleaned 'Conteudo' column ---
    mask_leia_mais_and_marcas_a_ignorar = final_df_setor_filtered['Conteudo'].apply(
        lambda x: check_leia_mais_and_marcas_a_ignorar(x, marcas_a_ignorar)
    )
    # --- End of modification ---

    # Filtrar o DataFrame para remover as linhas que correspondem à condição
    final_df_setor_filtered = final_df_setor_filtered[~mask_leia_mais_and_marcas_a_ignorar].copy()

    # O DataFrame 'final_df_setor_filtered' agora contém os dados após todas as filtragens.


    print(f"Número de registros antes da filtragem: {len(final_df_setor)}")
    print(f"Número de registros após a filtragem: {len(final_df_setor_filtered)}")

    # Você pode renomeá-lo para final_df_setor se quiser substituir o original.
    final_df_setor = final_df_setor_filtered.copy()

    # ↑↑↑↑↑↑↑↑↑↑ FINAL DO TRECHO PARA DESPREZAR REGISTROS DO ARQUIVO DE SETOR ↑↑↑↑↑↑↑↑↑↑↑↑↑↑

    # Grava o DataFrame final em um arquivo Excel

    #final_df_setor.to_excel(arq_api_original_setor, index=False)

    # Criar o DataFrame 'final_df_small' após a filtragem
    final_df_setor_small = final_df_setor[['Id', 'Titulo', 'Conteudo', 'IdVeiculo']].copy()

    return final_df_setor, final_df_setor_small

    #final_df_setor_small.to_excel(arq_api_setor, index=False)

    #print("Arquivo Excel salvo como ", arq_api_original_setor)
    #print("Arquivo Excel salvo como ", arq_api_setor)