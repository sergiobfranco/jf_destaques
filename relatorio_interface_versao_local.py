import streamlit as st
import subprocess
import datetime
import time
import sys
import os

# Configuração da página
st.set_page_config(
    page_title="Processador de Relatórios",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Processador de Relatórios")

# Opções de relatório
tipos_relatorio = {
    "Completo": "completo",
    "Estadão": "estadao", 
    "Folha": "folha",
    "Valor": "valor",
    "Globo": "globo"
}

# Interface
col1, col2 = st.columns([1, 2])

with col1:
    tipo_selecionado = st.selectbox(
        "Tipo de Relatório:",
        list(tipos_relatorio.keys())
    )
    
    st.info(f"**{tipo_selecionado}** selecionado")
    
    if st.button("🚀 Executar Relatório", use_container_width=True):
        # Comando para executar com caminho absoluto
        script_path = sys.executable  # Caminho do Python atual
        
        # Garantir caminho absoluto do arquivo
        pasta_atual = os.path.dirname(os.path.abspath(__file__))
        main_file = os.path.join(pasta_atual, "main_auto.py")
        
        # Verificar se o arquivo existe
        if not os.path.exists(main_file):
            st.error(f"❌ Arquivo não encontrado: {main_file}")
            st.stop()
        
        parametro = tipos_relatorio[tipo_selecionado]
        comando = [script_path, main_file, parametro]
        
        # Debug: mostrar informações do ambiente
        st.write(f"**Pasta atual:** `{pasta_atual}`")
        st.write(f"**Arquivo main:** `{main_file}`")
        st.write(f"**Comando:** `{' '.join(comando)}`")
        
        with col2:
            st.subheader("📋 Execução em Andamento")
            
            # Container para status e progress
            status_container = st.empty()
            progress_bar = st.progress(0)
            log_container = st.empty()
            
            status_container.info(f"🔄 Iniciando processamento de {tipo_selecionado}...")
            
            try:
                # Executar processo com encoding UTF-8
                processo = subprocess.Popen(
                    comando,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    cwd=pasta_atual,
                    env={**os.environ.copy(), 'PYTHONIOENCODING': 'utf-8'},  # Forçar UTF-8
                    encoding='utf-8',  # Especificar encoding
                    errors='replace'   # Substituir caracteres problemáticos
                )
                
                # Ler output linha por linha
                linhas_output = []
                linha_count = 0
                
                while True:
                    linha = processo.stdout.readline()
                    
                    if linha:
                        linhas_output.append(f"{datetime.datetime.now().strftime('%H:%M:%S')} - {linha.strip()}")
                        linha_count += 1
                        
                        # Atualizar progress bar (simulado)
                        progress = min(linha_count * 10, 90)  # máximo 90% até terminar
                        progress_bar.progress(progress)
                        
                        # Mostrar últimas linhas do log
                        log_text = "\n".join(linhas_output[-10:])  # últimas 10 linhas
                        log_container.code(log_text, language="bash")
                        
                        # Pequena pausa para não sobrecarregar a interface
                        time.sleep(0.1)
                        
                    elif processo.poll() is not None:
                        break
                
                # Processo terminou
                codigo_saida = processo.poll()
                progress_bar.progress(100)
                
                if codigo_saida == 0:
                    status_container.success(f"✅ Relatório {tipo_selecionado} concluído com sucesso!")
                else:
                    status_container.error(f"❌ Erro no processamento (código: {codigo_saida})")
                
                # Mostrar log completo em expander
                if linhas_output:
                    with st.expander("📄 Log Completo", expanded=False):
                        st.code("\n".join(linhas_output), language="bash")
                        
            except Exception as e:
                status_container.error(f"💥 Erro: {str(e)}")
                progress_bar.progress(0)

with col2:
    if 'executar' not in locals():
        st.subheader("📋 Log de Execução")
        st.info("Clique em 'Executar Relatório' para ver o log aqui")

# Footer
st.markdown("---")
st.caption("Sistema de Relatórios com Log em Tempo Real")