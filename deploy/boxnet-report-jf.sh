#!/bin/bash

# Configurações
PROJECT_DIR="/home/boxadmin/jf-relatorio"
LOG_BASE_DIR="/mnt/datasense-data/containers/boxnet-report-jf/logs"
SERVICE_NAME="boxnet-report-jf"
RETENTION_DAYS=30

# Criar diretório de logs se não existir
mkdir -p "$LOG_BASE_DIR"

# Configurar timezone para São Paulo
export TZ="America/Sao_Paulo"
export PATH=/usr/local/bin:/usr/bin:/bin

# Nome do arquivo de log com timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_BASE_DIR/jf-relatorio_${TIMESTAMP}.log"
LATEST_LOG="$LOG_BASE_DIR/latest.log"

# Função para log com timestamp
log_with_time() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S %Z')
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

# Função para limpeza de logs antigos
cleanup_old_logs() {
    log_with_time "Iniciando limpeza de logs antigos (>${RETENTION_DAYS} dias)"
    
    # Remover logs mais antigos que RETENTION_DAYS
    find "$LOG_BASE_DIR" -name "jf-relatorio_*.log" -type f -mtime +${RETENTION_DAYS} -delete
    
    local deleted_count=$(find "$LOG_BASE_DIR" -name "jf-relatorio_*.log" -type f -mtime +${RETENTION_DAYS} 2>/dev/null | wc -l)
    log_with_time "Limpeza concluída. Logs removidos: $deleted_count"
}

# Função para verificar se o diretório do projeto existe
check_project_dir() {
    if [ ! -d "$PROJECT_DIR" ]; then
        log_with_time "ERRO: Diretório do projeto '$PROJECT_DIR' não encontrado"
        return 1
    fi
    
    if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
        log_with_time "ERRO: Arquivo docker-compose.yml não encontrado em '$PROJECT_DIR'"
        return 1
    fi
    
    return 0
}

# Função para limpeza do Docker
docker_cleanup() {
    log_with_time "Iniciando limpeza do Docker..."
    
    # Para e remove containers órfãos
    cd "$PROJECT_DIR"
    docker compose down --remove-orphans >> "$LOG_FILE" 2>&1 || true
    
    # Remove imagens dangling
    docker image prune -f >> "$LOG_FILE" 2>&1 || true
    
    # Remove build cache antigo
    docker builder prune -a -f >> "$LOG_FILE" 2>&1 || true
    
    log_with_time "Limpeza do Docker concluída"
}

# Função para executar o build e execução
run_container_build() {
    log_with_time "Mudando para diretório do projeto: $PROJECT_DIR"
    cd "$PROJECT_DIR" || return 1
    
    log_with_time "Iniciando build e execução do container..."
    log_with_time "Comando: docker compose up --build --remove-orphans --abort-on-container-exit"
    log_with_time "NOTA: Logs do container serão capturados em tempo real"
    log_with_time "--- INÍCIO DA SAÍDA DO DOCKER COMPOSE E CONTAINERS ---"
    
    # Executar docker compose com build e capturar TODA a saída em tempo real
    local compose_exit_code=0
    
    # Usar processo em background para capturar logs em tempo real com timestamps
    {
        docker compose up --build --remove-orphans --abort-on-container-exit 2>&1 | while IFS= read -r line; do
            echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] [DOCKER] $line"
        done
        echo ${PIPESTATUS[0]} > /tmp/compose_exit_code_$
    } >> "$LOG_FILE" || compose_exit_code=$?
    
    # Capturar o exit code real do docker compose
    if [ -f "/tmp/compose_exit_code_$" ]; then
        compose_exit_code=$(cat "/tmp/compose_exit_code_$")
        rm -f "/tmp/compose_exit_code_$"
    fi
    
    log_with_time "--- FIM DA SAÍDA DO DOCKER COMPOSE E CONTAINERS ---"
    log_with_time "Exit code do docker compose: $compose_exit_code"
    
    # Garantir que os containers são derrubados
    log_with_time "Derrubando containers..."
    docker compose down --remove-orphans >> "$LOG_FILE" 2>&1 || true
    
    return $compose_exit_code
}

# Função principal
main() {
    log_with_time "=========================================="
    log_with_time "INICIANDO PROCESSAMENTO BOXNET REPORT J&F"
    log_with_time "=========================================="
    log_with_time "Serviço: $SERVICE_NAME"
    log_with_time "Diretório do projeto: $PROJECT_DIR"
    log_with_time "Log: $LOG_FILE"
    log_with_time "Timezone: $(date +%Z) ($(date '+%Y-%m-%d %H:%M:%S'))"
    log_with_time "=========================================="
    
    # Limpeza de logs antigos
    cleanup_old_logs
    
    # Verificar diretório do projeto
    if ! check_project_dir; then
        log_with_time "Abortando execução devido a erro na verificação do projeto"
        exit 1
    fi
    
    log_with_time "Diretório do projeto verificado com sucesso"
    
    # Limpeza do Docker
    docker_cleanup
    
    # Marcar tempo de início
    start_time=$(date +%s)
    start_timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_with_time "Iniciando execução com rebuild..."
    
    # Executar build e execução
    if run_container_build; then
        # Sucesso
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        hours=$((duration / 3600))
        minutes=$(((duration % 3600) / 60))
        seconds=$((duration % 60))
        
        log_with_time "=========================================="
        log_with_time "PROCESSAMENTO CONCLUÍDO COM SUCESSO"
        log_with_time "=========================================="
        log_with_time "Início: $start_timestamp"
        log_with_time "Fim: $(date '+%Y-%m-%d %H:%M:%S')"
        log_with_time "Duração: ${hours}h ${minutes}m ${seconds}s"
        log_with_time "Status: SUCESSO"
        
        exit_code=0
    else
        # Erro
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        hours=$((duration / 3600))
        minutes=$(((duration % 3600) / 60))
        seconds=$((duration % 60))
        
        log_with_time "=========================================="
        log_with_time "ERRO NO PROCESSAMENTO"
        log_with_time "=========================================="
        log_with_time "Duração até falha: ${hours}h ${minutes}m ${seconds}s"
        log_with_time "Status: ERRO"
        
        exit_code=1
    fi
    
    # Criar link simbólico para o último log
    ln -sf "$LOG_FILE" "$LATEST_LOG"
    log_with_time "Link simbólico criado: $LATEST_LOG -> $LOG_FILE"
    
    log_with_time "=========================================="
    
    # Mostrar estatísticas dos logs
    total_logs=$(find "$LOG_BASE_DIR" -name "jf-relatorio_*.log" -type f | wc -l)
    oldest_log=$(find "$LOG_BASE_DIR" -name "jf-relatorio_*.log" -type f -printf '%T+ %p\n' 2>/dev/null | sort | head -1 | cut -d' ' -f2-)
    disk_usage=$(du -sh "$LOG_BASE_DIR" 2>/dev/null | cut -f1)
    
    log_with_time "Estatísticas dos logs:"
    log_with_time "  - Total de logs: $total_logs"
    log_with_time "  - Log mais antigo: $(basename "$oldest_log" 2>/dev/null || echo "Nenhum")"
    log_with_time "  - Espaço utilizado: $disk_usage"
    log_with_time "  - Diretório: $LOG_BASE_DIR"
    
    # Limpeza final do Docker
    log_with_time "Executando limpeza final..."
    docker_cleanup
    
    log_with_time "Processamento finalizado em $(date)"
    exit $exit_code
}

# Trap para capturar sinais
trap 'log_with_time "Recebido sinal de interrupção. Finalizando..."; docker compose down --remove-orphans 2>/dev/null || true; exit 130' INT TERM

# Executar função principal
main "$@"