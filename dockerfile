# Imagem base oficial do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app
COPY service_account.json /app/service_account.json

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando padrão ao iniciar o container
CMD ["python", "main_docker.py"]
