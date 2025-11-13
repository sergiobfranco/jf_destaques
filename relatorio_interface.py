import streamlit as st
import subprocess
import datetime
import time
import os

# Configuração da página
st.set_page_config(
    page_title="Processador de Relatórios",
    page_icon="📊",
    layout="centered"
)

# Título da aplicação
st.title("📊 Processador de Relatórios")
st.write("Selecione o tipo de relatório que deseja processar:")

# Opções de relatório
tipos_relatorio = {
    "Completo": "completo",
    "Estadão": "estadao", 
    "Folha": "folha",
    "Valor": "valor",
    "Globo": "globo"
}

# Interface de seleção
tipo_selecionado = st.selectbox(
    "Tipo de Relatório:",
    list(tipos_relatorio.keys())
)

# Mostrar informações sobre o relatório selecionado
st.info(f"Relatório selecionado: **{tipo_selecionado}**")

# Botão para executar
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Executar Relatório", use_container_width=True):
        
        # Mostrar status de execução
        with st.spinner(f'Processando relatório {tipo_selecionado}...'):
            
            # Aqui você chamará seu script .sh com o parâmetro do tipo de relatório
            try:
                # Exemplo de como chamar seu script
                # Substitua pelo caminho real do seu script
                script_path = "/caminho/para/seu/script.sh"
                parametro = tipos_relatorio[tipo_selecionado]
                
                # Comando que será executado
                comando = [script_path, parametro]
                
                # Executar o comando
                resultado = subprocess.run(
                    comando, 
                    capture_output=True, 
                    text=True, 
                    timeout=300  # timeout de 5 minutos
                )
                
                # Verificar se executou com sucesso
                if resultado.returncode == 0:
                    st.success(f"✅ Relatório {tipo_selecionado} processado com sucesso!")
                    st.write("**Saída do processo:**")
                    st.code(resultado.stdout)
                    
                    # Log da execução
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.write(f"Executado em: {timestamp}")
                    
                else:
                    st.error(f"❌ Erro ao processar o relatório {tipo_selecionado}")
                    st.write("**Erro:**")
                    st.code(resultado.stderr)
                    
            except subprocess.TimeoutExpired:
                st.error("⏰ Timeout: O processamento demorou mais que o esperado")
                
            except FileNotFoundError:
                st.error("📁 Script não encontrado. Verifique o caminho do arquivo.")
                
            except Exception as e:
                st.error(f"💥 Erro inesperado: {str(e)}")

# Seção de informações
st.markdown("---")
st.subheader("ℹ️ Informações")

# Status do sistema
col1, col2 = st.columns(2)
with col1:
    st.metric("Servidor", "Online ✅")
with col2:
    st.metric("Docker", "Ativo ✅")  # Você pode fazer isso dinâmico depois

# Histórico (opcional - você pode implementar depois)
with st.expander("📋 Últimas Execuções"):
    st.write("Esta seção pode mostrar o histórico de execuções...")

# Footer
st.markdown("---")
st.caption("Sistema de Relatórios - Versão 1.0")