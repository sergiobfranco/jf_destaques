import os
import sys
from dotenv import load_dotenv

# Detectar base_dir mesmo dentro do .exe
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

import pandas as pd
import json
import requests
import time
from cronometro import obter_timestamp_brasilia, calcular_tempo_decorrido
from temporizador import aguardar_data_futura
from limpeza_marcas import limpar_marcas
from limpeza_setor import limpar_setor
from limpeza_editoriais_descartar import limpar_editoriais
from limpeza_specials import limpar_specials
from relevancia import avaliar_relevancia
from resumos_marcas_v2 import agrupar_noticias_por_similaridade
from prompts_setor import gerar_prompts_setor
from resumos_setor import gerar_resumos_setor
from relatorio_preliminar_segmentado import gerar_versao_preliminar
from relatorio_ajustado_final import gerar_versao_ajustada
from config import arq_api_original, arq_api, arq_api_irrelevantes, arq_results, arq_results_irrelevantes, arq_api_original_setor, arq_api_setor, arq_prompts_setor, \
    arq_results_setor, arq_api_original_editorial, arq_api_editorial, arq_api_original_SPECIALS, arq_api_SPECIALS, arq_resumo_final, arq_api_original_raw

def abrir_arquivos_gerados():
    final_df = pd.read_excel(arq_api_original)
    final_df_small = pd.read_excel(arq_api)
    final_df_small_irrelevantes = pd.read_excel(arq_api_irrelevantes)
    df_resumos_marcas = pd.read_excel(arq_results)
    df_resumos_marcas_irrelevantes = pd.read_excel(arq_results_irrelevantes)
    final_df_setor = pd.read_excel(arq_api_original_setor)
    final_df_small_setor = pd.read_excel(arq_api_setor)
    df_resumos_setor = pd.read_excel(arq_results_setor)
    final_df_editoriais = pd.read_excel(arq_api_original_editorial)
    final_df_small_editoriais = pd.read_excel(arq_api_editorial)
    final_df_specials = pd.read_excel(arq_api_original_SPECIALS)
    final_df_small_specials = pd.read_excel(arq_api_SPECIALS)
    return (final_df, final_df_small, final_df_small_irrelevantes, df_resumos_marcas, df_resumos_marcas_irrelevantes,
        final_df_setor, final_df_small_setor, df_resumos_setor, final_df_editoriais, final_df_small_editoriais,
        final_df_specials, final_df_small_specials)


def carregar_configs(caminho_json):
    with open(caminho_json, 'r', encoding='utf-8') as f:
        return json.load(f)

def consultar_apis(configs, max_tentativas=5):
    lista_df = []
    for config in configs:
        url = config.get("url")
        data = config.get("data")
        print(f"Consultando API: {url}")
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                dados = response.json()
                df_api = pd.DataFrame(dados)
                lista_df.append(df_api)
                print(f"✔️ Sucesso: {len(df_api)} registros")
            else:
                print(f"❌ Erro {response.status_code} para URL: {url}")
        except Exception as e:
            print(f"❌ Exceção ao consultar {url}: {str(e)}")
    return pd.concat(lista_df, ignore_index=True) if lista_df else pd.DataFrame()

def main():
    # 1. Aguarda a data e hora futura fornecida pelo operador
    #print('↓' * 94)
    #momento_inicial = input('Você deseja: (1) Iniciar imediatamente ou (2) Aguardar uma data e hora futuras? Digite 1 ou 2: ')
    #if momento_inicial not in ['1', '2']:
    #    print("Opção inválida. Encerrando o programa.")
    #    return
    #elif momento_inicial == '2':
    #    segundos_para_esperar = aguardar_data_futura()
    #    # Aguardar se for no futuro
    #    if segundos_para_esperar > 0:
    #        horas = segundos_para_esperar / 60 / 60
    #        print(f"Faltam {horas:.2f} horas até a data e hora futuras especificadas em São Paulo.")
    #        print("Aguardando...")
    #        time.sleep(segundos_para_esperar)
    #        print("Espera terminada. O código continuará a execução.")
    #    else:
    #        print("Continuando imediatamente pois a data especificada já passou.")
    
    # Pegar o timestamp atual em Brasília
    ts = obter_timestamp_brasilia()
    print("Timestamp atual:", ts)

    # 2. Chamada de API de MARCAS
    caminho_json = "dados/config/api_marca_configs.json"
    configs = carregar_configs(caminho_json)
    marcas_df = consultar_apis(configs)
    # Save raw API output for audit / replay
    try:
        marcas_df.to_excel(arq_api_original_raw, index=False)
        print(f"Saved raw marcas API output: {arq_api_original_raw} ({len(marcas_df)} records)")
    except Exception as e:
        print(f"Warning: could not save raw marcas file: {e}")

    final_df, final_df_small_bruto = limpar_marcas(marcas_df)
    final_df.to_excel(arq_api_original, index=False)

    # 3. Avaliação de RELEVÂNCIA
    final_df_small, final_df_small_irrelevantes = avaliar_relevancia(final_df_small_bruto)
    final_df_small.to_excel(arq_api, index=False)
    final_df_small_irrelevantes.to_excel(arq_api_irrelevantes, index=False)

    # 4.A Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Relevantes
    df_resumos_marcas = agrupar_noticias_por_similaridade(final_df_small)
    df_resumos_marcas.to_excel(arq_results, index=False)

    # 4.B Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Irrelevantes
    df_resumos_marcas_irrelevantes = agrupar_noticias_por_similaridade(final_df_small_irrelevantes)
    #df_resumos_marcas_irrelevantes.to_excel(arq_results_irrelevantes, index=False)
    #df_resumos_marcas_irrelevantes = agrupar_noticias_por_similaridade(final_df_small_irrelevantes)

    if df_resumos_marcas_irrelevantes is not None and not df_resumos_marcas_irrelevantes.empty:
        df_resumos_marcas_irrelevantes.to_excel(arq_results_irrelevantes, index=False)
    else:
        print("⚠️ Nenhuma notícia irrelevante encontrada. Gerando arquivo vazio com cabeçalho.")
        colunas = ["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"]
        pd.DataFrame(columns=colunas).to_excel(arq_results_irrelevantes, index=False)


    # 5. Chamada de API de SETOR
    caminho_json = "dados/config/api_setor_configs.json"
    configs = carregar_configs(caminho_json)
    setor_df = consultar_apis(configs)

    # Salvar arquivo raw de SETOR antes da limpeza (sanitizando caracteres inválidos)
    from config import arq_api_original_setor_raw
    import re
    def _sanitize_value_for_excel(x):
        if pd.isna(x):
            return x
        try:
            s = str(x)
            return re.sub(r'[\uD800-\uDFFF]', '', s)
        except Exception:
            try:
                return str(x).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            except Exception:
                return str(x)

    try:
        setor_df_safe = setor_df.copy()
        for col in setor_df_safe.columns:
            if setor_df_safe[col].dtype == object:
                setor_df_safe[col] = setor_df_safe[col].apply(_sanitize_value_for_excel)

        setor_df_safe.to_excel(arq_api_original_setor_raw, index=False)
        print(f"Saved raw setor API output: {arq_api_original_setor_raw} ({len(setor_df)} records)")
    except Exception as e:
        print(f"Warning: could not save raw setor file: {e}")

    final_df_setor, final_df_small_setor = limpar_setor(setor_df)
    final_df_setor.to_excel(arq_api_original_setor, index=False)
    final_df_small_setor.to_excel(arq_api_setor, index=False)

    # 6. Agrupa notícias de SETOR por SIMILARIDADE e gera PROMPTS para resumos
    df_prompts_setor = gerar_prompts_setor(final_df_small_setor)
    df_prompts_setor.to_excel(arq_prompts_setor, index=False)

    # 7. Processa RESUMOS de notícias de SETOR
    df_resumos_setor = gerar_resumos_setor(df_prompts_setor)
    df_resumos_setor.to_excel(arq_results_setor, index=False)

    # 8. Chamada de API de EDITORIAIS
    caminho_json = "dados/config/api_editorial_configs.json"
    configs = carregar_configs(caminho_json)
    editoriais_df = consultar_apis(configs)
    final_df_editoriais, final_df_small_editoriais = limpar_editoriais(editoriais_df)
    final_df_editoriais.to_excel(arq_api_original_editorial, index=False)
    final_df_small_editoriais.to_excel(arq_api_editorial, index=False)

    # 9. Chamada de API de SPECIALS
    caminho_json = "dados/config/api_SPECIALS_configs.json"
    configs = carregar_configs(caminho_json)
    specials_df = consultar_apis(configs)
    final_df_specials, final_df_small_specials = limpar_specials(specials_df)
    final_df_specials.to_excel(arq_api_original_SPECIALS, index=False)
    final_df_small_specials.to_excel(arq_api_SPECIALS, index=False)

    # 10. Geração do RELATÓRIO DE DESTAQUES
    # Carrega os dados necessários para o relatório
    (final_df, final_df_small, final_df_small_irrelevantes, df_resumos_marcas, df_resumos_marcas_irrelevantes,
    final_df_setor, final_df_small_setor, df_resumos_setor, final_df_editoriais, final_df_small_editoriais,
    final_df_specials, final_df_small_specials) = abrir_arquivos_gerados()

    # Ajustes de tipos de campos
    df_short = pd.read_excel('dados/api/shorturls_por_id.xlsx')
    final_df_small['Id'] = final_df_small['Id'].astype(int)
    df_short['Id'] = df_short['Id'].astype(int)
    final_df_small = final_df_small.merge(df_short, on=['Id', 'Canais'], how='left')

    gerar_versao_preliminar(final_df_small, final_df_small_irrelevantes, df_resumos_marcas, df_resumos_marcas_irrelevantes, final_df, df_resumos_setor, final_df_setor, final_df_editoriais, final_df_small_specials )
    
    # 11. Geração da Versão Ajustada do RELATÓRIO DE DESTAQUES
    PASTA_ID_DRIVE = "1BdPoC3HZ7rIVd_0cgEVl4xGIjimVXTmq"  # Se quiser upload automático
    gerar_versao_ajustada(arq_resumo_final, pasta_id_drive=PASTA_ID_DRIVE)    
    #gerar_versao_ajustada(arq_resumo_final)

    # Calcular o tempo decorrido desde aquele timestamp
    resultado = calcular_tempo_decorrido(ts)
    print(f"Tempo decorrido: {resultado['segundos']:.2f} segundos")
    print(f"                  {resultado['minutos']:.2f} minutos")
    print(f"                  {resultado['horas']:.2f} horas")
    #input("Fim do processamento. Pressione Enter para sair.")
if __name__ == "__main__":

    main()

