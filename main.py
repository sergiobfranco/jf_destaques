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
from limpeza_editoriais import limpar_editoriais
from limpeza_specials import limpar_specials
from relevancia import avaliar_relevancia
from resumos_marcas_v2 import agrupar_noticias_por_similaridade
from prompts_setor import gerar_prompts_setor
from resumos_setor import gerar_resumos_setor
from relatorio_preliminar import gerar_versao_preliminar
from relatorio_ajustado_final import gerar_versao_ajustada
from config import arq_api_original, arq_api, arq_api_irrelevantes, arq_results, arq_results_irrelevantes, arq_api_original_setor, arq_api_setor, arq_prompts_setor, \
    arq_results_setor, arq_api_original_editorial, arq_api_editorial, arq_api_original_SPECIALS, arq_api_SPECIALS, arq_resumo_final

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

import requests
import time
import pandas as pd

def consultar_apis(configs, max_tentativas=3, timeout_base=30):
    """
    Consulta APIs com retry automático e timeouts progressivos
    Versão simplificada sem dependências extras
    
    Args:
        configs: Lista de configurações das APIs
        max_tentativas: Número máximo de tentativas por API
        timeout_base: Timeout base em segundos
    """
    lista_df = []
    
    for i, config in enumerate(configs):
        url = config.get("url")
        data = config.get("data")
        print(f"Consultando API {i+1}/{len(configs)}: {url}")
        
        sucesso = False
        
        for tentativa in range(1, max_tentativas + 1):
            try:
                # Timeout progressivo: 30s, 60s, 90s
                timeout_atual = timeout_base + (tentativa - 1) * 30
                
                print(f"  Tentativa {tentativa}/{max_tentativas} (timeout: {timeout_atual}s)")
                
                response = requests.post(
                    url, 
                    json=data, 
                    timeout=timeout_atual
                )
                
                if response.status_code == 200:
                    dados = response.json()
                    df_api = pd.DataFrame(dados)
                    lista_df.append(df_api)
                    print(f"  ✅ Sucesso: {len(df_api)} registros")
                    sucesso = True
                    break
                    
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Códigos que justificam retry
                    print(f"  ⚠️ Status {response.status_code} - Tentativa {tentativa}")
                    if tentativa < max_tentativas:
                        espera = 5 + (tentativa * 2)  # 7s, 9s, 11s
                        print(f"  ⏳ Aguardando {espera}s...")
                        time.sleep(espera)
                else:
                    # Outros códigos de erro - não faz retry
                    print(f"  ❌ Erro {response.status_code} para URL: {url}")
                    break
                    
            except requests.exceptions.Timeout:
                print(f"  ⏱️ Timeout após {timeout_atual}s na tentativa {tentativa}")
                if tentativa < max_tentativas:
                    espera = 10 * tentativa  # 10s, 20s, 30s
                    print(f"  ⏳ Aguardando {espera}s antes da próxima tentativa...")
                    time.sleep(espera)
                    
            except requests.exceptions.ConnectionError as e:
                erro_str = str(e)[:100]
                print(f"  🔌 Erro de conexão na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    espera = 15 * tentativa  # 15s, 30s, 45s
                    print(f"  ⏳ Aguardando {espera}s antes da próxima tentativa...")
                    time.sleep(espera)
                    
            except requests.exceptions.RequestException as e:
                erro_str = str(e)[:100]
                print(f"  ❌ Erro de requisição na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    time.sleep(5 * tentativa)
                    
            except Exception as e:
                erro_str = str(e)[:100]
                print(f"  ❌ Erro inesperado na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    time.sleep(3 * tentativa)
        
        if not sucesso:
            print(f"  ❌ FALHA: Todas as {max_tentativas} tentativas falharam para {url}")
            print(f"  ⚠️ Continuando com as próximas APIs...")
    
    if lista_df:
        resultado = pd.concat(lista_df, ignore_index=True)
        print(f"\n📊 Total consolidado: {len(resultado)} registros de {len(lista_df)} APIs bem-sucedidas")
        return resultado
    else:
        print(f"\n⚠️ Nenhuma API retornou dados válidos")
        return pd.DataFrame()


def main():
    # 1. Aguarda a data e hora futura fornecida pelo operador
    print('↓' * 94)
    momento_inicial = input('Você deseja: (1) Iniciar imediatamente ou (2) Aguardar uma data e hora futuras? Digite 1 ou 2: ')
    if momento_inicial not in ['1', '2']:
        print("Opção inválida. Encerrando o programa.")
        return
    elif momento_inicial == '2':
        segundos_para_esperar = aguardar_data_futura()
        # Aguardar se for no futuro
        if segundos_para_esperar > 0:
            horas = segundos_para_esperar / 60 / 60
            print(f"Faltam {horas:.2f} horas até a data e hora futuras especificadas em São Paulo.")
            print("Aguardando...")
            time.sleep(segundos_para_esperar)
            print("Espera terminada. O código continuará a execução.")
        else:
            print("Continuando imediatamente pois a data especificada já passou.")
    
    # Pegar o timestamp atual em Brasília
    ts = obter_timestamp_brasilia()
    print("Timestamp atual:", ts)

    # 2. Chamada de API de MARCAS
    caminho_json = "dados/config/api_marca_configs.json"
    configs = carregar_configs(caminho_json)
    marcas_df = consultar_apis(configs)

    if marcas_df.empty:
        print("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de MARCAS!")
        print("📝 Criando DataFrame de MARCAS vazio com estrutura padrão...")
        colunas_marcas = [
            'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
        ]
        marcas_df = pd.DataFrame(columns=colunas_marcas)
        final_df = marcas_df.copy()
        final_df_small_bruto = marcas_df.copy()
        print("✅ DataFrames vazios criados com sucesso para MARCAS")
    else:
        print(f"✅ {len(marcas_df)} registros obtidos para MARCAS")
        final_df, final_df_small_bruto = limpar_marcas(marcas_df)

    final_df.to_excel(arq_api_original, index=False)

    # 3. Avaliação de RELEVÂNCIA

    print(f"📊 final_df tem {len(final_df)} registros")
    print(f"📊 final_df_small_bruto tem {len(final_df_small_bruto)} registros")

    if marcas_df.empty:
        print("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de MARCAS!")
        print("📝 Criando DataFrame de RELEVÂNCIA vazio com estrutura padrão...")
        colunas_relevancia = [
            'Id', 'Titulo', 'Conteudo', 'IdVeiculo', 'Canais', 'TextoCompleto', 'RelevanciaMarca'
        ]
        relevancia_df = pd.DataFrame(columns=colunas_relevancia)
        final_df_small = relevancia_df.copy()
        final_df_small_irrelevantes = relevancia_df.copy()
        print("✅ DataFrames vazios de RELEVÂNCIA criados com sucesso para MARCAS")
    else:
        final_df_small, final_df_small_irrelevantes = avaliar_relevancia(final_df_small_bruto)

    print(f"📊 final_df_small tem {len(final_df_small)} registros")
    print(f"📊 final_df_small_irrelevantes tem {len(final_df_small_irrelevantes)} registros")


    final_df_small.to_excel(arq_api, index=False)
    final_df_small_irrelevantes.to_excel(arq_api_irrelevantes, index=False)

    # 4.A Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Relevantes
    if final_df_small.empty:
        colunas_resumos = [
            'Marca', 'GrupoID', 'QtdNoticias', 'Ids', 'Resumo'
        ]
        df_resumos_marcas = pd.DataFrame(columns=colunas_resumos)
    else:
        df_resumos_marcas = agrupar_noticias_por_similaridade(final_df_small)

    print(f"📊 df_resumos_marcas resultante tem {len(df_resumos_marcas)} registros")

    df_resumos_marcas.to_excel(arq_results, index=False)

    # 4.B Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Irrelevantes
    if final_df_small_irrelevantes.empty:
        colunas_resumos = [
            'Marca', 'GrupoID', 'QtdNoticias', 'Ids', 'Resumo'
        ]
        df_resumos_marcas_irrelevantes = pd.DataFrame(columns=colunas_resumos)
    else:
        df_resumos_marcas_irrelevantes = agrupar_noticias_por_similaridade(final_df_small_irrelevantes)

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

    if setor_df.empty:
        print("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de SETOR!")
        print("📝 Criando DataFrame de SETOR vazio com estrutura padrão...")
        colunas_setor = [
            'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
        ]
        setor_df = pd.DataFrame(columns=colunas_setor)
        final_df_setor = setor_df.copy()
        final_df_small_setor = setor_df.copy()
        print("✅ DataFrames vazios criados com sucesso para SETOR")
    else:
        print(f"✅ {len(setor_df)} registros obtidos para SETOR")
        final_df_setor, final_df_small_setor = limpar_setor(setor_df)

    final_df_setor.to_excel(arq_api_original_setor, index=False)
    final_df_small_setor.to_excel(arq_api_setor, index=False)

    # 6. Agrupa notícias de SETOR por SIMILARIDADE e gera PROMPTS para resumos
    if final_df_small_setor.empty:
        df_prompts_setor = pd.DataFrame(columns=['Id', 'Tipo', 'Prompt', 'Tema', 'RelevanceScore', 'IdVeiculo'])
    else:
        df_prompts_setor = gerar_prompts_setor(final_df_small_setor)
    df_prompts_setor.to_excel(arq_prompts_setor, index=False)

    # 7. Processa RESUMOS de notícias de SETOR
    if df_prompts_setor.empty:
        df_resumos_setor = pd.DataFrame(columns=['Tema', 'Id', 'Resumo'])
    else:
        df_resumos_setor = gerar_resumos_setor(df_prompts_setor)
    df_resumos_setor.to_excel(arq_results_setor, index=False)

    # 8. Chamada de API de EDITORIAIS
    caminho_json = "dados/config/api_editorial_configs.json"
    configs = carregar_configs(caminho_json)
    editoriais_df = consultar_apis(configs)

    if editoriais_df.empty:
        print("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de EDITORIAIS!")
        print("📝 Criando DataFrame de EDITORIAIS vazio com estrutura padrão...")
        colunas_editoriais = [
            'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
        ]
        editoriais_df = pd.DataFrame(columns=colunas_editoriais)
        final_df_editoriais = editoriais_df.copy()
        final_df_small_editoriais = editoriais_df.copy()
        print("✅ DataFrames vazios criados com sucesso para EDITORIAIS")
    else:
        print(f"✅ {len(editoriais_df)} registros obtidos para EDITORIAIS")
        final_df_editoriais, final_df_small_editoriais = limpar_editoriais(editoriais_df)

    final_df_editoriais.to_excel(arq_api_original_editorial, index=False)
    final_df_small_editoriais.to_excel(arq_api_editorial, index=False)

    # 9. Chamada de API de SPECIALS
    caminho_json = "dados/config/api_SPECIALS_configs.json"
    configs = carregar_configs(caminho_json)
    specials_df = consultar_apis(configs)

    if specials_df.empty:
        print("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de SPECIALS!")
        print("📝 Criando DataFrame de SPECIALS vazio com estrutura padrão...")
        colunas_specials = [
            'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
        ]
        specials_df = pd.DataFrame(columns=colunas_specials)
        final_df_specials = specials_df.copy()
        final_df_small_specials = specials_df.copy()
        print("✅ DataFrames vazios criados com sucesso para SPECIALS")
    else:
        print(f"✅ {len(specials_df)} registros obtidos para SPECIALS")
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

    # Calcular o tempo decorrido desde aquele timestamp
    resultado = calcular_tempo_decorrido(ts)
    print(f"Tempo decorrido: {resultado['segundos']:.2f} segundos")
    print(f"                  {resultado['minutos']:.2f} minutos")
    print(f"                  {resultado['horas']:.2f} horas")
    input("Fim do processamento. Pressione Enter para sair.")
if __name__ == "__main__":

    main()

