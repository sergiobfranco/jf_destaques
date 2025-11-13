.PHONY: default build run full clean nuke activate check

# Caminho do docker-compose.yml (se quiser customizar)
COMPOSE_FILE=docker-compose.yml

# Diretório onde os logs serão salvos
LOG_DIR=logs

# Data/hora atual formatada
TIMESTAMP=$(shell date +"%Y-%m-%d_%H-%M-%S")

# Alvo padrão: executa normalmente
default: run

# Ativa ambiente virtual e checa
activate:
	@powershell -Command "& .\venv\Scripts\Activate.ps1; Get-Command python"

check:
	@powershell -Command "Get-Command python"

# Apenas build da imagem
build:
	docker-compose -f $(COMPOSE_FILE) build --no-cache
	docker image prune --filter "dangling=true" --force

# Executa e salva log com timestamp
run:
	@mkdir -p $(LOG_DIR)
	@echo "▶️ Executando e salvando log em $(LOG_DIR)/run_$(TIMESTAMP).log"
	docker-compose -f $(COMPOSE_FILE) up --abort-on-container-exit > $(LOG_DIR)/run_$(TIMESTAMP).log 2>&1

# Build + run com log
full:
	@mkdir -p $(LOG_DIR)
	@echo "🛠️ Build + Run com log em $(LOG_DIR)/full_$(TIMESTAMP).log"
	docker-compose -f $(COMPOSE_FILE) up --build --abort-on-container-exit > $(LOG_DIR)/full_$(TIMESTAMP).log 2>&1

# Limpa containers parados, imagens, volumes, redes órfãs
clean:
	docker system prune -f

# Remove tudo: containers, volumes, imagens
nuke:
	docker-compose -f $(COMPOSE_FILE) down -v --rmi all --remove-orphans
