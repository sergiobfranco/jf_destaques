# Versão Prelimnar do Relatório

import pandas as pd
import pyshorteners
from docx import Document
from docx.shared import Pt  # Import Pt for point size
from docx.enum.text import WD_LINE_SPACING  # Import line spacing enum
import re
import time # Importar time para pausa
from config import arq_resumo_final, marca1, marca2
import requests
import os
from datetime import datetime

def gerar_versao_preliminar(final_df_small_marca, final_df_small_marca_irrelevantes, df_resumo_marca, df_resumo_marca_irrelevantes, final_df_marca, df_resumo_setor, final_df_setor, final_df_editorial, final_df_SPECIALS_small):
    # 1. Carregar os DataFrames
    #df_resumo_marca = pd.read_excel(arq_results_final) # Renomeado para clareza
    #final_df_marca = pd.read_excel(arq_api_original) # Renomeado para clareza
    #df_resumo_setor = pd.read_excel(arq_results_setor) # Carregar resultados do setor
    #final_df_setor = pd.read_excel(arq_api_original_setor) # Carregar dados originais do setor
    #final_df_editorial = pd.read_excel(arq_api_original_editorial) # Carregar dados originais dos editoriais
    #final_df_SPECIALS_small = pd.read_excel(arq_api_SPECIALS) # Carregar dados dos SPECIALS


    # Load the final_df_small generated in the MARCA section
    # We assume arq_api points to the small excel file from the MARCA section
    #try:
    #    final_df_small_marca = pd.read_excel(arq_api)
    #except FileNotFoundError:
    #    print(f"Erro: Arquivo {arq_api} não encontrado. Certifique-se de que a seção de MARCA foi executada.")
    #    # You might want to exit or handle this case differently
    #    final_df_small_marca = pd.DataFrame() # Create empty DataFrame to avoid further errors


    # 2. Inicializar o documento DOCX
    document = Document()

    # Configurar o estilo Normal para remover espaço após o parágrafo e usar espaçamento simples
    styles = document.styles
    style = styles['Normal']
    font = style.font
    font.name = 'Calibri'  # Set the font to Calibri
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    # Adicionar título e linha em branco
    document.add_paragraph("DESTAQUES DO DIA J&F")
    document.add_paragraph("")
    document.add_paragraph("--- NOTÍCIAS DE MARCAS ---")
    document.add_paragraph("")

    # --- Seção Original para resumos de Marca ---
    # 3. Iterar sobre df_resumo (Marca)
    print(f"Processando {len(df_resumo_marca)} resumos de Marca...") # Debug print
    for index, row_marca in df_resumo_marca.iterrows(): # Renomeado para clareza
        # Inicializar a string para cada grupo de notícias
        group_string = ""

        # 4. Iterar sobre os IDs das notícias (Marca)
        # Check if 'Ids' column exists and is not None
        if 'Ids' not in row_marca or pd.isna(row_marca['Ids']):
            print(f"Aviso: Linha {index} no df_resumo_marca não tem IDs válidos. Pulando.")
            continue

        for news_id_str in str(row_marca['Ids']).split(','): # Ensure it's a string
            try:
                news_id = int(news_id_str.strip())  # Convert to integer, strip whitespace
            except ValueError:
                print(f"Aviso: Não foi possível converter ID '{news_id_str}' para inteiro na linha {index} de df_resumo_marca. Pulando.")
                continue # Skip this ID if not a valid number


            # 5. Consultar informações no final_df_marca
            # Use final_df_marca for original info (like Veiculo, UrlVisualizacao, CanaisCommodities)
            news_info_marca = final_df_marca[final_df_marca['Id'] == news_id]
            if news_info_marca.empty:
                print(f"Aviso: ID {news_id} não encontrado em final_df_marca para resumo de Marca. Pulando.")
                continue # Skip this news if not found

            news_info_marca = news_info_marca.iloc[0]

            w_veiculo_marca = news_info_marca['Veiculo']
            w_url_marca = news_info_marca['UrlVisualizacao']
            #w_canais_commodities_marca = news_info_marca['CanaisCommodities'] # Obter CanaisCommodities (se disponível)


            # 6. Encurtar a URL
            s = pyshorteners.Shortener()
            retries = 3  # Number of retries
            short_url_marca = w_url_marca # Inicializa com a URL original
            for i in range(retries):
                try:
                    short_url_marca = s.tinyurl.short(w_url_marca)
                    break  # Exit the loop if successful
                except requests.exceptions.RequestException as e:
                    # Check if the error is due to a redirect or other network issue
                    if "Read timed out" in str(e) or "connection" in str(e) or "Max retries exceeded" in str(e):
                        print(f"Erro de conexão/timeout ao encurtar URL (tentativa {i+1}/{retries}) para Marca ID {news_id}: {e}")
                    else:
                        print(f"Erro ao encurtar URL (tentativa {i+1}/{retries}) para Marca ID {news_id}: {e}")

                    if i < retries - 1:
                        time.sleep(2)  # Wait before retrying
                    else:
                        print(f"Falha ao encurtar URL para Marca ID {news_id} após {retries} tentativas. Usando URL original.")
                        short_url_marca = w_url_marca # Use original URL if all retries fail


            # **Atualizar o DataFrame arq_api** (Atualiza final_df_small_marca)
            # Certifica-se de que a linha existe antes de tentar atualizar
            if news_id in final_df_small_marca['Id'].values:
                final_df_small_marca.loc[final_df_small_marca['Id'] == news_id, 'ShortURL'] = short_url_marca
            else:
                # This might happen if the small DF was filtered differently or not generated correctly
                print(f"Aviso: ID {news_id} não encontrado em final_df_small_marca para adicionar ShortURL. Ignorando atualização do ShortURL neste DF.")
                # Optionally, add the news info to final_df_small_marca if it's missing
                # new_row = news_info_marca.copy()
                # new_row['ShortURL'] = short_url_marca
                # final_df_small_marca = pd.concat([final_df_small_marca, pd.DataFrame([new_row])], ignore_index=True)


            # 7. Criar a string formatada

            # Incluir trecho de código para identificar o tipo "Special"
            special_type = ""
            # Busca o Id no final_df_SPECIALS_small
            special_info = final_df_SPECIALS_small[final_df_SPECIALS_small['Id'] == news_id]

            if not special_info.empty:
                # Se encontrar, verifica o campo Canais
                # Certifica-se de que 'Canais' é uma lista ou string e a processa
                canais_special = special_info.iloc[0]['Canais']
                if isinstance(canais_special, list):
                    canais_str = ', '.join(map(str, canais_special)) # Converte lista para string
                else:
                    canais_str = str(canais_special) # Garante que é string


                if "Editoriais" in canais_str:
                    special_type = "Editorial"
                elif "Colunistas" in canais_str:
                    special_type = "Colunista"
                elif "1ª Página" in canais_str:
                    special_type = "Capa"
                # Se não contiver nenhuma das strings acima, special_type permanece ""

            # Formata a string incluindo o tipo "Special" se encontrado
            if special_type:
                group_string += f"{w_veiculo_marca} ({special_type} - {short_url_marca}), "
            else:
                group_string += f"{w_veiculo_marca} ({short_url_marca}), "


        # 8. Limpar e adicionar o resumo à string
        # Remover a última vírgula e espaço da string de veículos/urls
        group_string = group_string.rstrip(', ')
        group_string += "\n" # Adicionar quebra de linha antes do resumo

        # Check if 'Resumo' column exists and is not None
        if 'Resumo' not in row_marca or pd.isna(row_marca['Resumo']):
            print(f"Aviso: Linha {index} no df_resumo_marca não tem Resumo. Adicionando placeholder.")
            resumo_limpo = "[Resumo não disponível]"
        else:
            resumo_limpo = str(row_marca['Resumo']) # Ensure it's string first
            # Remove the specific string and strip whitespace - This is handled in the final processing step now
            # resumo_limpo = resumo_limpo.replace("(160 palavras)", "").strip()


        group_string += resumo_limpo

        # 9. Adicionar a string ao documento DOCX
        document.add_paragraph(group_string)
        document.add_paragraph("")  # Adicionar linha em branco




    # 99. --- Seção Original para resumos de Marca - NOTÍCIAS IRRELEVANTES ---
    # 3. Iterar sobre df_resumo (Marca)

    document.add_paragraph("")
    document.add_paragraph("--- CITAÇÕES ---") # Opcional: um título para a seção de links
    document.add_paragraph("")
    
    print(f"Processando {len(df_resumo_marca_irrelevantes)} resumos de Marca - CITAÇÕES ...") # Debug print
    for index, row_marca in df_resumo_marca_irrelevantes.iterrows(): # Renomeado para clareza
        # Inicializar a string para cada grupo de notícias
        group_string = ""

        # 4. Iterar sobre os IDs das notícias (Marca)
        # Check if 'Ids' column exists and is not None
        if 'Ids' not in row_marca or pd.isna(row_marca['Ids']):
            print(f"Aviso: Linha {index} no df_resumo_marca_irrelevantes não tem IDs válidos. Pulando.")
            continue

        for news_id_str in str(row_marca['Ids']).split(','): # Ensure it's a string
            try:
                news_id = int(news_id_str.strip())  # Convert to integer, strip whitespace
            except ValueError:
                print(f"Aviso: Não foi possível converter ID '{news_id_str}' para inteiro na linha {index} de df_resumo_marca. Pulando.")
                continue # Skip this ID if not a valid number


            # 5. Consultar informações no final_df_marca
            # Use final_df_marca for original info (like Veiculo, UrlVisualizacao, CanaisCommodities)
            news_info_marca = final_df_marca[final_df_marca['Id'] == news_id]
            if news_info_marca.empty:
                print(f"Aviso: ID {news_id} não encontrado em final_df_marca para resumo de Marca. Pulando.")
                continue # Skip this news if not found

            news_info_marca = news_info_marca.iloc[0]

            w_veiculo_marca = news_info_marca['Veiculo']
            w_url_marca = news_info_marca['UrlVisualizacao']
            #w_canais_commodities_marca = news_info_marca['CanaisCommodities'] # Obter CanaisCommodities (se disponível)


            # 6. Encurtar a URL
            s = pyshorteners.Shortener()
            retries = 3  # Number of retries
            short_url_marca = w_url_marca # Inicializa com a URL original
            for i in range(retries):
                try:
                    short_url_marca = s.tinyurl.short(w_url_marca)
                    break  # Exit the loop if successful
                except requests.exceptions.RequestException as e:
                    # Check if the error is due to a redirect or other network issue
                    if "Read timed out" in str(e) or "connection" in str(e) or "Max retries exceeded" in str(e):
                        print(f"Erro de conexão/timeout ao encurtar URL (tentativa {i+1}/{retries}) para Marca ID {news_id}: {e}")
                    else:
                        print(f"Erro ao encurtar URL (tentativa {i+1}/{retries}) para Marca ID {news_id}: {e}")

                    if i < retries - 1:
                        time.sleep(2)  # Wait before retrying
                    else:
                        print(f"Falha ao encurtar URL para Marca ID {news_id} após {retries} tentativas. Usando URL original.")
                        short_url_marca = w_url_marca # Use original URL if all retries fail


            # **Atualizar o DataFrame arq_api** (Atualiza final_df_small_marca_irrelevantes)
            # Certifica-se de que a linha existe antes de tentar atualizar
            if news_id in final_df_small_marca_irrelevantes['Id'].values:
                final_df_small_marca_irrelevantes.loc[final_df_small_marca_irrelevantes['Id'] == news_id, 'ShortURL'] = short_url_marca
            else:
                # This might happen if the small DF was filtered differently or not generated correctly
                print(f"Aviso: ID {news_id} não encontrado em final_df_small_marca_irrelevantes para adicionar ShortURL. Ignorando atualização do ShortURL neste DF.")
                # Optionally, add the news info to final_df_small_marca if it's missing
                # new_row = news_info_marca.copy()
                # new_row['ShortURL'] = short_url_marca
                # final_df_small_marca = pd.concat([final_df_small_marca, pd.DataFrame([new_row])], ignore_index=True)


            # 7. Criar a string formatada

            # Incluir trecho de código para identificar o tipo "Special"
            special_type = ""
            # Busca o Id no final_df_SPECIALS_small
            special_info = final_df_SPECIALS_small[final_df_SPECIALS_small['Id'] == news_id]

            if not special_info.empty:
                # Se encontrar, verifica o campo Canais
                # Certifica-se de que 'Canais' é uma lista ou string e a processa
                canais_special = special_info.iloc[0]['Canais']
                if isinstance(canais_special, list):
                    canais_str = ', '.join(map(str, canais_special)) # Converte lista para string
                else:
                    canais_str = str(canais_special) # Garante que é string


                if "Editoriais" in canais_str:
                    special_type = "Editorial"
                elif "Colunistas" in canais_str:
                    special_type = "Colunista"
                elif "1ª Página" in canais_str:
                    special_type = "Capa"
                # Se não contiver nenhuma das strings acima, special_type permanece ""

            # Formata a string incluindo o tipo "Special" se encontrado
            if special_type:
                group_string += f"{w_veiculo_marca} ({special_type} - {short_url_marca}), "
            else:
                group_string += f"{w_veiculo_marca} ({short_url_marca}), "


        # 8. Limpar e adicionar o resumo à string
        # Remover a última vírgula e espaço da string de veículos/urls
        group_string = group_string.rstrip(', ')
        group_string += "\n" # Adicionar quebra de linha antes do resumo

        # Check if 'Resumo' column exists and is not None
        if 'Resumo' not in row_marca or pd.isna(row_marca['Resumo']):
            print(f"Aviso: Linha {index} no df_resumo_marca_irrelevantes não tem Resumo. Adicionando placeholder.")
            resumo_limpo = "[Resumo não disponível]"
        else:
            resumo_limpo = str(row_marca['Resumo']) # Ensure it's string first
            # Remove the specific string and strip whitespace - This is handled in the final processing step now
            # resumo_limpo = resumo_limpo.replace("(160 palavras)", "").strip()


        group_string += resumo_limpo

        # 9. Adicionar a string ao documento DOCX
        document.add_paragraph(group_string)
        document.add_paragraph("")  # Adicionar linha em branco


    # --- Fim da Seção Original para resumos de Marca - NOTÍCIAS IRRELEVANTES ---

    # --- Início da seção links das notícias por Marcas ---
    # Juntar os dois dataframes de notícias de marca (relevantes e irrelevantes)
    final_df_small_marca_combined = pd.concat([final_df_small_marca, final_df_small_marca_irrelevantes], ignore_index=True)

    # DEBUG: Check final_df_small_marca_combined before sorting
    print(f"\nVerificando final_df_small_marca_combined antes de ordenar para links:")
    print(f"  Tem {len(final_df_small_marca_combined)} linhas.")
    print(f"  Tem coluna 'Canais'? {'Canais' in final_df_small_marca_combined.columns}")

    if not final_df_small_marca_combined.empty and 'Canais' in final_df_small_marca_combined.columns:
        try:
            order = [marca1, marca2] + [marca for marca in final_df_small_marca_combined['Canais'].unique() if marca not in (marca1, marca2)]
            final_df_small_marca_sorted = final_df_small_marca_combined.sort_values(by=['Canais'], key=lambda x: pd.Categorical(x, categories=order, ordered=True))
            print("Ordenação personalizada dos links por Marca aplicada.")

            #print("Conteúdo de final_df_small_marca_sorted gerado try:")
            #print(final_df_small_marca_sorted[['Canais', 'Veiculo', 'Titulo', 'Link']])

        except (NameError, KeyError, AttributeError) as e:
            print(f"Aviso: Falha na ordenação personalizada dos links por Marca ({type(e).__name__}: {e}). Verifique se marca1, marca2 e w_marcas estão definidos corretamente.")
            print("Ordenando por Canais padrão.")
            final_df_small_marca_sorted = final_df_small_marca_combined.sort_values(by=['Canais'])

            #print("Conteúdo de final_df_small_marca_sorted gerado try:")
            #print(final_df_small_marca_sorted[['Canais', 'Veiculo', 'Titulo', 'Link']])

        document.add_paragraph("")
        document.add_paragraph("--- LINKS DAS NOTÍCIAS DE MARCA ---")
        document.add_paragraph("")

        current_marca = None

        for index, row_small_marca in final_df_small_marca_sorted.iterrows():
            marca = row_small_marca['Canais']
            if marca != current_marca:
                if current_marca is not None:
                    document.add_paragraph("")
                document.add_paragraph(f"*{marca}*")
                current_marca = marca

            news_id_small = row_small_marca['Id']
            original_row_marca = final_df_marca[final_df_marca['Id'] == news_id_small]
            if original_row_marca.empty:
                print(f"Aviso: ID {news_id_small} não encontrado em final_df_marca para links de Marca. Pulando este link.")
                continue

            original_row_marca = original_row_marca.iloc[0]

            veiculo = original_row_marca['Veiculo']
            titulo = original_row_marca['Titulo']
            canais_commodities = original_row_marca.get('CanaisCommodities', '')

            document.add_paragraph(f"{veiculo}: {titulo}")

            short_url = row_small_marca.get('ShortURL')
            if pd.isna(short_url) or not short_url:
                short_url = original_row_marca.get('UrlVisualizacao', 'URL Não Encontrada')

            prefix = "Coluna - " if "Colunistas" in str(canais_commodities) else ""
            document.add_paragraph(f"{prefix}{short_url}")

            document.add_paragraph("*")
    else:
        print("DataFrame 'final_df_small_marca_combined' não encontrado, vazio ou sem a coluna 'Canais'. Pulando a seção de links por Marcas.")

    # --- Fim da seção links das notícias por Marcas ---


    # --- Novo Passo: Incluir resumos do Setor ---
    # DEBUG: Check if df_resumo_setor is populated
    print(f"\nVerificando df_resumo_setor:")
    print(f"  Tem {len(df_resumo_setor)} linhas.")
    print(f"  Está vazio? {df_resumo_setor.empty}")
    if not df_resumo_setor.empty:
        document.add_paragraph("")
        document.add_paragraph("--- NOTÍCIAS DE SETOR ---") # Opcional: um título para a seção de setor
        document.add_paragraph("")


    # 10. Iterar o dataframe arq_results_setor (já deve estar ordenado por Tema)
    current_tema = None  # Inicializar variável para controlar o tema atual

    # Use df_resumo_setor, not arq_results_setor
    for index, row_setor in df_resumo_setor.iterrows():
        # Check if 'Tema' column exists and is not None
        if 'Tema' not in row_setor or pd.isna(row_setor['Tema']):
            print(f"Aviso: Linha {index} no df_resumo_setor não tem Tema. Pulando.")
            continue

        tema = row_setor['Tema']

        # 11. Quando iniciar um Tema novo, incluir uma linha com o conteúdo do campo Tema, precedido e sucedido por um asterisco.
        if tema != current_tema:
            if current_tema is not None: # Adicionar linha em branco entre temas
                document.add_paragraph("")
            document.add_paragraph(f"*{tema}*")
            current_tema = tema

        # 12. Buscar informações no final_df_setor usando o Id
        # Check if 'Id' column exists and is not None
        if 'Id' not in row_setor or pd.isna(row_setor['Id']):
            print(f"Aviso: Linha {index} no df_resumo_setor não tem Id válido. Pulando.")
            continue

        try:
            news_id = int(str(row_setor['Id']).strip()) # Convert to integer, ensure string then strip
        except ValueError:
            print(f"Aviso: Não foi possível converter ID '{row_setor['Id']}' para inteiro na linha {index} de df_resumo_setor. Pulando.")
            continue # Skip this ID if not a valid number

        news_info_setor = final_df_setor[final_df_setor['Id'] == news_id]
        if news_info_setor.empty:
            print(f"Aviso: ID {news_id} não encontrado em final_df_setor para resumo de Setor. Pulando.")
            continue # Skip this news if not found
        news_info_setor = news_info_setor.iloc[0]

        w_veiculo_setor = news_info_setor['Veiculo']
        w_titulo_setor = news_info_setor['Titulo']
        w_url_setor = news_info_setor['UrlVisualizacao']

        # 13. Incluir linha com Veiculo e Titulo
        document.add_paragraph(f"{w_veiculo_setor}: {w_titulo_setor}")

        # 14. Incluir o Resumo do Setor
        # Check if 'Resumo' column exists and is not None
        if 'Resumo' not in row_setor or pd.isna(row_setor['Resumo']):
            print(f"Aviso: Linha {index} no df_resumo_setor (Tema {tema}) não tem Resumo. Adicionando placeholder.")
            document.add_paragraph("[Resumo não disponível]")
        else:
            resumo_bruto = str(row_setor['Resumo'])
            # Remove prefix like "**Resumo (90 palavras):**" or "**Resumo (160 palavras):**"
            # This pattern is now covered by the more general removal later.
            # Removing specific prefixes here might be redundant or interfere with the final step.
            # Keeping the raw resumo to be processed in the final cleanup loop.
            document.add_paragraph(resumo_bruto) # Add raw resumo, will be processed later


        # 15. Incluir a URL encurtada (Encapsular a lógica de encurtamento)
        s = pyshorteners.Shortener()
        retries = 3
        short_url_setor = w_url_setor # Inicializa com a URL original
        for i in range(retries):
            try:
                short_url_setor = s.tinyurl.short(w_url_setor)
                break
            except requests.exceptions.RequestException as e:
                # Check if the error is due to a redirect or other network issue
                if "Read timed out" in str(e) or "connection" in str(e) or "Max retries exceeded" in str(e):
                    print(f"Erro de conexão/timeout ao encurtar URL (tentativa {i+1}/{retries}) para Setor ID {news_id}: {e}")
                else:
                    print(f"Erro ao encurtar URL (tentativa {i+1}/{retries}) para Setor ID {news_id}: {e}")
                if i < retries - 1:
                    time.sleep(2)
                else:
                    print(f"Falha ao encurtar URL para Setor ID {news_id} após {retries} tentativas. Usando URL original.")

        document.add_paragraph(short_url_setor)

        # 16. Incluir a linha com um asterisco
        document.add_paragraph("*")



    # --- Novo Passo: Incluir Editoriais ---
    print(f"\nProcessando {len(final_df_editorial)} editoriais...")
    if not final_df_editorial.empty:
        document.add_paragraph("")
        document.add_paragraph("*EDITORIAIS*")
        document.add_paragraph("") # Linha em branco após o título dos editoriais

        for index, row_editorial in final_df_editorial.iterrows():
            # 17. Incluir uma linha com o conteúdo do campo Veiculo, mais a string ": ", mais o conteúdo do campo Conteudo
            w_veiculo_editorial = row_editorial.get('Veiculo', 'Veículo Desconhecido')
            w_conteudo_editorial = row_editorial.get('Titulo', 'Título não disponível')
            document.add_paragraph(f"{w_veiculo_editorial}: {w_conteudo_editorial}")

            # 18. Incluir uma linha com a url encurtada do conteúdo do campo UrlVisualizacao
            w_url_editorial = row_editorial.get('UrlVisualizacao', 'URL Não Disponível')

            s = pyshorteners.Shortener()
            retries = 3
            short_url_editorial = w_url_editorial
            for i in range(retries):
                try:
                    short_url_editorial = s.tinyurl.short(w_url_editorial)
                    break
                except requests.exceptions.RequestException as e:
                    if "Read timed out" in str(e) or "connection" in str(e) or "Max retries exceeded" in str(e):
                        print(f"Erro de conexão/timeout ao encurtar URL (tentativa {i+1}/{retries}) para Editorial {index}: {e}")
                    else:
                        print(f"Erro ao encurtar URL (tentativa {i+1}/{retries}) para Editorial {index}: {e}")
                    if i < retries - 1:
                        time.sleep(2)
                    else:
                        print(f"Falha ao encurtar URL para Editorial {index} após {retries} tentativas. Usando URL original.")

            document.add_paragraph(short_url_editorial)
            document.add_paragraph("*") # Adicionar linha com asterisco após cada editorial



    # ===== PROCESSAMENTO DO DOCUMENTO ANTES DA GRAVAÇÃO =====
    # Este código deve ser inserido logo antes da linha: document.save(arq_resumo_final)

    print("\nProcessando documento antes da gravação para remover padrões...")

    paragraphs_to_remove_indices = []  # Lista de índices para remoção

    # Pattern for lines starting with "*(" and ending with "palavras)"
    pattern_line_start_paren_end_palavras = r"^\s*\*\s*\(.*?palavras\)\s*$"
    # Pattern for lines starting with "*Resumo"
    pattern_line_start_resumo = r"^\s*\*Resumo.*$"
    # Pattern for any occurrence of "(*...palavras*)" or "(...palavras)" or "**Resumo (...):**" etc.
    # Let's refine this to catch various formats
    pattern_parenthesized_palavras_general = r"\s*[\*\s]*\(.*?\s*palavras\s*\)[\s\:\*]*"
    # Add patterns for specific prefixes like "**Resumo:**" or "*Resumo:*"
    pattern_specific_resumo_prefixes = r"^\s*[\*\s]*Resumo\s*[:\*\s]*"


    for i, paragraph in enumerate(document.paragraphs):
        texto = paragraph.text

        # 1) Eliminar todas as linhas que começam com a string "*(" E terminam com a string "palavras)"
        if re.fullmatch(pattern_line_start_paren_end_palavras, texto, re.IGNORECASE):
            paragraphs_to_remove_indices.append(i)
            print(f"  Removendo linha {i} por corresponder ao padrão '* (... palavras)'")
            continue # Skip further processing for this paragraph

        # 2) Eliminar as linhas que começam com a string "*Resumo"
        if re.fullmatch(pattern_line_start_resumo, texto, re.IGNORECASE):
            paragraphs_to_remove_indices.append(i)
            print(f"  Removendo linha {i} por começar com '*Resumo'")
            continue # Skip further processing for this paragraph


        # 3) Eliminar as strings que começam com a string "*(", e que tenham algum conteúdo na sequência, e em seguida encerrem com a string "palavras)"
        # Also handle patterns like "**Resumo (...):**" and "*Resumo:*"
        new_text = re.sub(pattern_parenthesized_palavras_general, '', texto, flags=re.IGNORECASE).strip()
        new_text = re.sub(pattern_specific_resumo_prefixes, '', new_text, flags=re.IGNORECASE).strip()


        # If the text changed, update the paragraph
        if new_text != texto.strip(): # Compare with stripped original text
            paragraph.text = new_text
            print(f"  Removido padrão '(... palavras)' ou prefixos de resumo na linha {i}")

        # Replace any remaining "**" with "*"
        if "**" in paragraph.text:
            paragraph.text = paragraph.text.replace("**", "*")
            # print(f"  Substituído '**' por '*' na linha {i}") # Optional debug print


    # Remover os parágrafos marcados para remoção (em ordem reversa)
    for i in sorted(paragraphs_to_remove_indices, reverse=True):
        p = document.paragraphs[i]._element
        p.getparent().remove(p)

    print(f"\nTotal de parágrafos removidos: {len(paragraphs_to_remove_indices)}")


    # 3. Agora salvar o documento processado
    # Gerar novo nome de arquivo com timestamp antes do sufixo .docx
    #base, ext = os.path.splitext(arq_resumo_final)
    #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #arq_resumo_final_timestamp = f"{base}_{timestamp}{ext}"
    document.save(arq_resumo_final)

    # 19. Salvar o documento DOCX
    # document.save(arq_resumo_final) # Já salvo acima
    print(f"Arquivo DOCX salvo em: {arq_resumo_final}")

    #return arq_resumo_final_timestamp  # Retornar o caminho do arquivo salvo para uso posterior