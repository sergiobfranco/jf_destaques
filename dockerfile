# Imagem base oficial do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app
COPY service_account.json /app/service_account.json

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expor a porta do Streamlit
EXPOSE 8561

# Comando padrão ao iniciar o container (agora com Streamlit)
CMD ["streamlit", "run", "main_menu.py", "--server.port=8561", "--server.address=0.0.0.0"]
