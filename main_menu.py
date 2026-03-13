import streamlit as st
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
import fcntl
import datetime
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
from relatorio_preliminar_segmentado import gerar_versao_preliminar
from relatorio_ajustado_final import gerar_versao_ajustada
from config import arq_api_original, arq_api, arq_api_irrelevantes, arq_results, arq_results_irrelevantes, arq_api_original_setor, arq_api_setor, arq_prompts_setor, \
    arq_results_setor, arq_api_original_editorial, arq_api_editorial, arq_api_original_SPECIALS, arq_api_SPECIALS, arq_resumo_final
from config import arq_api_original_raw

# Variável global para armazenar a opção selecionada
opcao_selecionada = None

LOCK_FILE = '/tmp/jf_relatorio.lock'

def adquirir_lock():
    try:
        lock_file = open(LOCK_FILE, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(f"PID: {os.getpid()}\n")
        lock_file.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        lock_file.flush()
        return lock_file
    except IOError:
        return None

def liberar_lock(lock_file):
    if lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
        except:
            pass
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except:
            pass

def verificar_lock_ativo():
    if not os.path.exists(LOCK_FILE):
        return False
    try:
        test_lock = open(LOCK_FILE, 'r')
        fcntl.flock(test_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(test_lock.fileno(), fcntl.LOCK_UN)
        test_lock.close()
        os.remove(LOCK_FILE)
        return False
    except IOError:
        return True
    except:
        return False


def configurar_interface():
    """Configura a interface Streamlit"""
    st.set_page_config(
        page_title="Gerador de Relatórios J&F",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🗞️ Gerador de Relatórios J&F")
    st.markdown("---")

def selecionar_opcao():
    """Interface para seleção do tipo de relatório"""
    global opcao_selecionada
    
    if st.session_state.get('processamento_em_andamento', False) or verificar_lock_ativo():
        st.error("⚠️ PROCESSAMENTO JÁ EM ANDAMENTO!")
        return False
    
    
    st.subheader("Selecione o tipo de relatório a ser gerado:")
    
    opcoes = {
        1: "📊 Relatório Completo",
        2: "🏢 Somente Marcas",
        3: "🏭 Somente Setor",
        4: "📰 Setor - Estadão",
        5: "💰 Setor - Valor Econômico",
        6: "📄 Setor - Folha de SP",
        7: "🌎 Setor - O Globo",
        8: "❌ Sair da Aplicação"
    }
    
    # Layout em colunas para melhor organização
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Opções Principais:**")
        for key in [1, 2, 3]:
            if st.button(opcoes[key], key=f"btn_{key}", use_container_width=True):
                opcao_selecionada = key
                st.session_state.opcao_selecionada = key
                st.rerun()
    
    with col2:
        st.write("**Opções Específicas de Veículos:**")
        for key in [4, 5, 6, 7]:
            if st.button(opcoes[key], key=f"btn_{key}", use_container_width=True):
                opcao_selecionada = key
                st.session_state.opcao_selecionada = key
                st.rerun()
    
    # Botão de sair em linha separada para dar destaque
    st.markdown("---")
    col_exit = st.columns([2, 1, 2])[1]  # Centralizar o botão
    with col_exit:
        if st.button(opcoes[8], key="btn_exit", type="secondary", use_container_width=True):
            st.session_state.opcao_selecionada = 8
            opcao_selecionada = 8
            st.rerun()
    
    # Verificar se a opção de sair foi selecionada
    if 'opcao_selecionada' in st.session_state and st.session_state.opcao_selecionada == 8:
        st.error("🚪 Saindo da aplicação...")
        st.info("Para fechar completamente, feche a aba do navegador ou pressione Ctrl+C no terminal.")
        st.stop()  # Para a execução do Streamlit
    
    # Mostrar opção selecionada (exceto para sair)
    if 'opcao_selecionada' in st.session_state and st.session_state.opcao_selecionada != 8:
        opcao_selecionada = st.session_state.opcao_selecionada
        st.success(f"✅ Opção selecionada: **{opcoes[opcao_selecionada]}**")
        
        if st.button("🚀 Iniciar Processamento", type="primary", use_container_width=True, disabled=st.session_state.get('processamento_em_andamento', False)):
            st.session_state.processamento_em_andamento = True
            return True
    
    return False

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
        st.info(f"Consultando API {i+1}/{len(configs)}: {url}")
        
        sucesso = False
        
        for tentativa in range(1, max_tentativas + 1):
            try:
                # Timeout progressivo: 30s, 60s, 90s
                timeout_atual = timeout_base + (tentativa - 1) * 30
                
                st.write(f"  Tentativa {tentativa}/{max_tentativas} (timeout: {timeout_atual}s)")
                
                response = requests.post(
                    url, 
                    json=data, 
                    timeout=timeout_atual
                )
                
                if response.status_code == 200:
                    dados = response.json()
                    df_api = pd.DataFrame(dados)
                    lista_df.append(df_api)
                    st.success(f"  ✅ Sucesso: {len(df_api)} registros")
                    sucesso = True
                    break
                    
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Códigos que justificam retry
                    st.warning(f"  ⚠️ Status {response.status_code} - Tentativa {tentativa}")
                    if tentativa < max_tentativas:
                        espera = 5 + (tentativa * 2)  # 7s, 9s, 11s
                        st.write(f"  ⏳ Aguardando {espera}s...")
                        time.sleep(espera)
                else:
                    # Outros códigos de erro - não faz retry
                    st.error(f"  ❌ Erro {response.status_code} para URL: {url}")
                    break
                    
            except requests.exceptions.Timeout:
                st.warning(f"  ⏱️ Timeout após {timeout_atual}s na tentativa {tentativa}")
                if tentativa < max_tentativas:
                    espera = 10 * tentativa  # 10s, 20s, 30s
                    st.write(f"  ⏳ Aguardando {espera}s antes da próxima tentativa...")
                    time.sleep(espera)
                    
            except requests.exceptions.ConnectionError as e:
                erro_str = str(e)[:100]
                st.warning(f"  🔌 Erro de conexão na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    espera = 15 * tentativa  # 15s, 30s, 45s
                    st.write(f"  ⏳ Aguardando {espera}s antes da próxima tentativa...")
                    time.sleep(espera)
                    
            except requests.exceptions.RequestException as e:
                erro_str = str(e)[:100]
                st.error(f"  ❌ Erro de requisição na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    time.sleep(5 * tentativa)
                    
            except Exception as e:
                erro_str = str(e)[:100]
                st.error(f"  ❌ Erro inesperado na tentativa {tentativa}: {erro_str}...")
                if tentativa < max_tentativas:
                    time.sleep(3 * tentativa)
        
        if not sucesso:
            st.error(f"  ❌ FALHA: Todas as {max_tentativas} tentativas falharam para {url}")
            st.warning(f"  ⚠️ Continuando com as próximas APIs...")
    
    if lista_df:
        resultado = pd.concat(lista_df, ignore_index=True)
        st.success(f"\n📊 Total consolidado: {len(resultado)} registros de {len(lista_df)} APIs bem-sucedidas")
        return resultado
    else:
        st.warning(f"\n⚠️ Nenhuma API retornou dados válidos")
        return pd.DataFrame()

def processar_relatorio():
    """Função principal de processamento baseada na opção selecionada"""
    lock = None
    lock = adquirir_lock()
    if lock is None:
        st.error("⚠️ Outro processamento em andamento!")
        st.session_state.processamento_em_andamento = False
        return
    
    global opcao_selecionada
    
    if 'opcao_selecionada' not in st.session_state:
        st.error("Nenhuma opção foi selecionada!")
        return
    
    opcao_selecionada = st.session_state.opcao_selecionada

    # Mapear opções para códigos de veículo
    codigo_veiculo = None
    if opcao_selecionada == 4:  # Setor - Estadão
        codigo_veiculo = 675
    elif opcao_selecionada == 5:  # Setor - Valor Econômico
        codigo_veiculo = 10459
    elif opcao_selecionada == 6:  # Setor - Folha de SP
        codigo_veiculo = 331
    elif opcao_selecionada == 7:  # Setor - O Globo
        codigo_veiculo = 682

    # Pegar o timestamp atual em Brasília
    ts = obter_timestamp_brasilia()
    st.write("Timestamp atual:", ts)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # TODO: Aqui você implementará a lógica condicional baseada na opcao_selecionada
        # Por enquanto, mantendo o processamento completo
        
        
        # Inicializar variáveis para controle de fluxo
        executar_marcas = opcao_selecionada in [1, 2]  # Relatório Completo ou Somente Marcas
        executar_setor = opcao_selecionada in [1, 3, 4, 5, 6, 7]  # Todas exceto Somente Marcas
        executar_editoriais = True  # Sempre executar
        executar_specials = True  # Sempre executar
        
        # Variáveis para armazenar dados processados
        final_df = pd.DataFrame()
        final_df_small = pd.DataFrame()
        final_df_small_irrelevantes = pd.DataFrame()
        df_resumos_marcas = pd.DataFrame()
        df_resumos_marcas_irrelevantes = pd.DataFrame()
        final_df_setor = pd.DataFrame()
        final_df_small_setor = pd.DataFrame()
        df_resumos_setor = pd.DataFrame()
        final_df_editoriais = pd.DataFrame()
        final_df_small_editoriais = pd.DataFrame()
        final_df_specials = pd.DataFrame()
        final_df_small_specials = pd.DataFrame()
        
        total_steps = 0
        current_step = 0
        
        # Calcular total de steps baseado na opção
        if executar_marcas:
            total_steps += 4  # 2, 3, 4A, 4B
        if executar_setor:
            total_steps += 3  # 5, 6, 7
        total_steps += 4  # 8, 9, 10, 11 (sempre executados)
        
        # ===== PROCESSAMENTO DE MARCAS =====
        if executar_marcas:
            status_text.text("Iniciando processamento das APIs de MARCAS...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            # 2. Chamada de API de MARCAS
            caminho_json = "dados/config/api_marca_configs.json"
            configs = carregar_configs(caminho_json)
            marcas_df = consultar_apis(configs)

            # Save raw API output for MARCAS (always save the raw payload before any cleaning)
            try:
                marcas_df.to_excel(arq_api_original_raw, index=False)
                st.info(f"💾 Favoritos (raw) de MARCAS salvos: {arq_api_original_raw} ({len(marcas_df)} registros)")
            except Exception as e:
                st.warning(f"⚠️ Não foi possível salvar arquivo raw de MARCAS: {e}")

            if marcas_df.empty:
                st.warning("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de MARCAS!")
                st.info("🔍 Criando DataFrame de MARCAS vazio com estrutura padrão...")
                colunas_marcas = [
                    'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
                ]
                marcas_df = pd.DataFrame(columns=colunas_marcas)
                final_df = marcas_df.copy()
                final_df_small_bruto = marcas_df.copy()
                st.success("✅ DataFrames vazios criados com sucesso para MARCAS")
            else:
                st.success(f"✅ {len(marcas_df)} registros obtidos para MARCAS")
                final_df, final_df_small_bruto = limpar_marcas(marcas_df)

            final_df.to_excel(arq_api_original, index=False)
            
            # 3. Avaliação de RELEVÂNCIA
            status_text.text("Processando avaliação de relevância...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            st.info(f"📊 final_df tem {len(final_df)} registros")
            st.info(f"📊 final_df_small_bruto tem {len(final_df_small_bruto)} registros")

            if marcas_df.empty:
                st.warning("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de MARCAS!")
                st.info("🔍 Criando DataFrame de RELEVÂNCIA vazio com estrutura padrão...")
                colunas_relevancia = [
                    'Id', 'Titulo', 'Conteudo', 'IdVeiculo', 'Canais', 'TextoCompleto', 'RelevanciaMarca'
                ]
                relevancia_df = pd.DataFrame(columns=colunas_relevancia)
                final_df_small = relevancia_df.copy()
                final_df_small_irrelevantes = relevancia_df.copy()
                st.success("✅ DataFrames vazios de RELEVÂNCIA criados com sucesso para MARCAS")
            else:
                final_df_small, final_df_small_irrelevantes = avaliar_relevancia(final_df_small_bruto)

            st.info(f"📊 final_df_small tem {len(final_df_small)} registros")
            st.info(f"📊 final_df_small_irrelevantes tem {len(final_df_small_irrelevantes)} registros")

            final_df_small.to_excel(arq_api, index=False)
            final_df_small_irrelevantes.to_excel(arq_api_irrelevantes, index=False)

            # 4.A Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Relevantes
            status_text.text("Agrupando notícias relevantes por similaridade...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            if final_df_small.empty:
                colunas_resumos = [
                    'Marca', 'GrupoID', 'QtdNoticias', 'Ids', 'Resumo'
                ]
                df_resumos_marcas = pd.DataFrame(columns=colunas_resumos)
            else:
                df_resumos_marcas = agrupar_noticias_por_similaridade(final_df_small)

            st.info(f"📊 df_resumos_marcas resultante tem {len(df_resumos_marcas)} registros")
            df_resumos_marcas.to_excel(arq_results, index=False)

            # 4.B Agrupa MARCAS por SIMILARIDADE e gera RESUMOS pelo DeepSeek - Notícias Irrelevantes
            status_text.text("Agrupando notícias irrelevantes por similaridade...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
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
                st.warning("⚠️ Nenhuma notícia irrelevante encontrada. Gerando arquivo vazio com cabeçalho.")
                colunas = ["Marca", "GrupoID", "QtdNoticias", "Ids", "Resumo"]
                pd.DataFrame(columns=colunas).to_excel(arq_results_irrelevantes, index=False)
        else:
            # Criar DataFrames vazios para MARCAS quando não processadas
            st.info("📋 Pulando processamento de MARCAS conforme opção selecionada")
            colunas_marcas = ['Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais']
            colunas_relevancia = ['Id', 'Titulo', 'Conteudo', 'IdVeiculo', 'Canais', 'TextoCompleto', 'RelevanciaMarca']
            colunas_resumos = ['Marca', 'GrupoID', 'QtdNoticias', 'Ids', 'Resumo']
            
            final_df = pd.DataFrame(columns=colunas_marcas)
            final_df_small = pd.DataFrame(columns=colunas_relevancia)
            final_df_small_irrelevantes = pd.DataFrame(columns=colunas_relevancia)
            df_resumos_marcas = pd.DataFrame(columns=colunas_resumos)
            df_resumos_marcas_irrelevantes = pd.DataFrame(columns=colunas_resumos)
            
            # Salvar DataFrames vazios
            final_df.to_excel(arq_api_original, index=False)
            final_df_small.to_excel(arq_api, index=False)
            final_df_small_irrelevantes.to_excel(arq_api_irrelevantes, index=False)
            df_resumos_marcas.to_excel(arq_results, index=False)
            df_resumos_marcas_irrelevantes.to_excel(arq_results_irrelevantes, index=False)

        # ===== PROCESSAMENTO DE SETOR =====
        if executar_setor:
            # 5. Chamada de API de SETOR
            status_text.text("Processando APIs de SETOR...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            # Determinar o arquivo de configuração baseado na opção selecionada
            if codigo_veiculo:
                # Para opções específicas de veículos, usar arquivo dedicado
                caminho_json = f"dados/config/api_setor_{codigo_veiculo}_configs.json"
                st.info(f"🎯 Usando configuração específica para veículo {codigo_veiculo}: {caminho_json}")
            else:
                # Para "Somente Setor" ou "Relatório Completo", usar arquivo geral
                caminho_json = "dados/config/api_setor_configs.json"
                st.info(f"📁 Usando configuração geral de setor: {caminho_json}")
            
            # Carregar configurações do arquivo apropriado
            try:
                configs = carregar_configs(caminho_json)
                st.success(f"✅ Carregadas {len(configs)} configurações de {caminho_json}")
            except FileNotFoundError:
                st.error(f"❌ Arquivo de configuração não encontrado: {caminho_json}")
                configs = []
            except Exception as e:
                st.error(f"❌ Erro ao carregar configurações de {caminho_json}: {str(e)}")
                configs = []
            
            setor_df = consultar_apis(configs)

            # Salvar arquivo raw de SETOR antes da limpeza
            from config import arq_api_original_setor_raw
            # Sanitizar strings para remover surrogates que quebram o writer (XML/OpenPyXL)
            import re
            def _sanitize_value_for_excel(x):
                if pd.isna(x):
                    return x
                try:
                    # For any value, convert to str then strip surrogate code points
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
                st.info(f"\ud83d\udcbe Favoritos (raw) de SETOR salvos: {arq_api_original_setor_raw} ({len(setor_df)} registros)")
            except Exception as e:
                st.warning(f"\u26a0\ufe0f N\u00e3o foi poss\u00edvel salvar arquivo raw de SETOR: {e}")

            if setor_df.empty:
                st.warning("\u26a0\ufe0f ATEN\u00c7\u00c3O: Nenhum registro retornado pelas APIs de SETOR!")
                st.info("🔍 Criando DataFrame de SETOR vazio com estrutura padrão...")
                colunas_setor = [
                    'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
                ]
                setor_df = pd.DataFrame(columns=colunas_setor)
                final_df_setor = setor_df.copy()
                final_df_small_setor = setor_df.copy()
                st.success("\u2705 DataFrames vazios criados com sucesso para SETOR")
            else:
                st.success(f"\u2705 {len(setor_df)} registros obtidos para SETOR")
                final_df_setor, final_df_small_setor = limpar_setor(setor_df)
            final_df_setor.to_excel(arq_api_original_setor, index=False)
            final_df_small_setor.to_excel(arq_api_setor, index=False)

            # 6. Agrupa notícias de SETOR por SIMILARIDADE e gera PROMPTS para resumos
            status_text.text("Gerando prompts para resumos de SETOR...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            if final_df_small_setor.empty:
                df_prompts_setor = pd.DataFrame(columns=['Id', 'Tipo', 'Prompt', 'Tema', 'RelevanceScore', 'IdVeiculo'])
            else:
                df_prompts_setor = gerar_prompts_setor(final_df_small_setor)
            df_prompts_setor.to_excel(arq_prompts_setor, index=False)

            # 7. Processa RESUMOS de notícias de SETOR
            status_text.text("Processando resumos de SETOR...")
            current_step += 1
            progress_bar.progress(int((current_step / total_steps) * 90))
            
            if df_prompts_setor.empty:
                df_resumos_setor = pd.DataFrame(columns=['Tema', 'Id', 'Resumo'])
            else:
                df_resumos_setor = gerar_resumos_setor(df_prompts_setor)
            df_resumos_setor.to_excel(arq_results_setor, index=False)
        else:
            # Criar DataFrames vazios para SETOR quando não processado
            st.info("📋 Pulando processamento de SETOR conforme opção selecionada")
            colunas_setor = ['Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais']
            colunas_prompts = ['Id', 'Tipo', 'Prompt', 'Tema', 'RelevanceScore', 'IdVeiculo']
            colunas_resumos_setor = ['Tema', 'Id', 'Resumo']
            
            final_df_setor = pd.DataFrame(columns=colunas_setor)
            final_df_small_setor = pd.DataFrame(columns=colunas_setor)
            df_prompts_setor = pd.DataFrame(columns=colunas_prompts)
            df_resumos_setor = pd.DataFrame(columns=colunas_resumos_setor)
            
            # Salvar DataFrames vazios
            final_df_setor.to_excel(arq_api_original_setor, index=False)
            final_df_small_setor.to_excel(arq_api_setor, index=False)
            df_prompts_setor.to_excel(arq_prompts_setor, index=False)
            df_resumos_setor.to_excel(arq_results_setor, index=False)

        # ===== PROCESSAMENTO DE EDITORIAIS (SEMPRE EXECUTADO) =====
        # 8. Chamada de API de EDITORIAIS
        status_text.text("Processando APIs de EDITORIAIS...")
        current_step += 1
        progress_bar.progress(int((current_step / total_steps) * 90))
        
        caminho_json = "dados/config/api_editorial_configs.json"
        configs = carregar_configs(caminho_json)
        editoriais_df = consultar_apis(configs)

        if editoriais_df.empty:
            st.warning("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de EDITORIAIS!")
            st.info("🔍 Criando DataFrame de EDITORIAIS vazio com estrutura padrão...")
            colunas_editoriais = [
                'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
            ]
            editoriais_df = pd.DataFrame(columns=colunas_editoriais)
            final_df_editoriais = editoriais_df.copy()
            final_df_small_editoriais = editoriais_df.copy()
            st.success("✅ DataFrames vazios criados com sucesso para EDITORIAIS")
        else:
            st.success(f"✅ {len(editoriais_df)} registros obtidos para EDITORIAIS")
            final_df_editoriais, final_df_small_editoriais = limpar_editoriais(editoriais_df)

        final_df_editoriais.to_excel(arq_api_original_editorial, index=False)
        final_df_small_editoriais.to_excel(arq_api_editorial, index=False)

        # ===== PROCESSAMENTO DE SPECIALS (SEMPRE EXECUTADO) =====
        # 9. Chamada de API de SPECIALS
        status_text.text("Processando APIs de SPECIALS...")
        current_step += 1
        progress_bar.progress(int((current_step / total_steps) * 90))
        
        caminho_json = "dados/config/api_SPECIALS_configs.json"
        configs = carregar_configs(caminho_json)
        specials_df = consultar_apis(configs)

        if specials_df.empty:
            st.warning("⚠️ ATENÇÃO: Nenhum registro retornado pelas APIs de SPECIALS!")
            st.info("🔍 Criando DataFrame de SPECIALS vazio com estrutura padrão...")
            colunas_specials = [
                'Id', 'Titulo', 'Conteudo', 'UrlOriginal', 'DataVeiculacao', 'IdVeiculo', 'Canais'
            ]
            specials_df = pd.DataFrame(columns=colunas_specials)
            final_df_specials = specials_df.copy()
            final_df_small_specials = specials_df.copy()
            st.success("✅ DataFrames vazios criados com sucesso para SPECIALS")
        else:
            st.success(f"✅ {len(specials_df)} registros obtidos para SPECIALS")
            final_df_specials, final_df_small_specials = limpar_specials(specials_df)

        final_df_specials.to_excel(arq_api_original_SPECIALS, index=False)
        final_df_small_specials.to_excel(arq_api_SPECIALS, index=False)

        # ===== GERAÇÃO DOS RELATÓRIOS (SEMPRE EXECUTADO) =====
        # 10. Geração do RELATÓRIO DE DESTAQUES
        status_text.text("Gerando relatório de destaques...")
        current_step += 1
        progress_bar.progress(int((current_step / total_steps) * 90))
        
        # Preparar dados para merge se necessário
        if not final_df_small.empty:
            try:
                df_short = pd.read_excel('dados/api/shorturls_por_id.xlsx')
                final_df_small['Id'] = final_df_small['Id'].astype(int)
                df_short['Id'] = df_short['Id'].astype(int)
                final_df_small = final_df_small.merge(df_short, on=['Id', 'Canais'], how='left')
            except FileNotFoundError:
                st.warning("⚠️ Arquivo shorturls_por_id.xlsx não encontrado. Continuando sem merge.")
            except Exception as e:
                st.warning(f"⚠️ Erro no merge com shorturls: {str(e)}")

        # Chamar gerar_versao_preliminar com parâmetros
        gerar_versao_preliminar(
            final_df_small, 
            final_df_small_irrelevantes, 
            df_resumos_marcas, 
            df_resumos_marcas_irrelevantes, 
            final_df, 
            df_resumos_setor, 
            final_df_setor, 
            final_df_editoriais, 
            final_df_small_specials,
            opcao_selecionada=opcao_selecionada,
            codigo_veiculo=codigo_veiculo
        )
        
        # 11. Geração da Versão Ajustada do RELATÓRIO DE DESTAQUES
        status_text.text("Gerando versão ajustada do relatório...")
        current_step += 1
        progress_bar.progress(100)
        
        PASTA_ID_DRIVE = "1BdPoC3HZ7rIVd_0cgEVl4xGIjimVXTmq"
        gerar_versao_ajustada(arq_resumo_final, pasta_id_drive=PASTA_ID_DRIVE)

        status_text.text("Processamento concluído!")

        # Calcular o tempo decorrido desde aquele timestamp
        resultado = calcular_tempo_decorrido(ts)
        
        st.success("🎉 Processamento concluído com sucesso!")
        st.info(f"⏱️ Tempo decorrido: {resultado['segundos']:.2f} segundos ({resultado['minutos']:.2f} minutos)")
        
        # Mostrar informações sobre a opção selecionada
        opcoes_nomes = {
            1: "Relatório Completo",
            2: "Somente Marcas", 
            3: "Somente Setor",
            4: "Setor - Estadão",
            5: "Setor - Valor Econômico", 
            6: "Setor - Folha de SP",
            7: "Setor - O Globo"
        }
        
        info_opcao = f"📋 Opção processada: **{opcoes_nomes[opcao_selecionada]}**"
        if codigo_veiculo:
            info_opcao += f" (Código do veículo: {codigo_veiculo})"
        
        st.info(info_opcao)
        
        st.session_state.processamento_em_andamento = False

    except Exception as e:
        st.error(f"❌ Erro durante o processamento: {str(e)}")
        st.exception(e)

    finally:
        liberar_lock(lock)

def main():
    """Função principal com interface Streamlit"""
    configurar_interface()
    
    # Verificar se deve sair antes de mostrar a interface
    if 'opcao_selecionada' in st.session_state and st.session_state.opcao_selecionada == 8:
        st.error("🚪 Aplicação encerrada pelo usuário")
        st.info("Para reiniciar, recarregue a página ou execute novamente o script.")
        st.stop()
    
    # Interface de seleção
    if selecionar_opcao():
        st.markdown("---")
        st.subheader("📊 Processamento em Andamento")
        processar_relatorio()

if __name__ == "__main__":
    main()