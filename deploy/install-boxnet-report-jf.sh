#!/bin/bash

# Script de instalação do serviço Boxnet J&F Report
set -e

SERVICE_NAME="boxnet-report-jf"
SCRIPT_PATH="/usr/local/bin/${SERVICE_NAME}.sh"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_PATH="/etc/systemd/system/${SERVICE_NAME}.timer"
LOG_DIR="/mnt/datasense-data/containers/boxnet-report-jf/logs"
PROJECT_DIR="/home/boxadmin/jf-relatorio"

echo "=========================================="
echo "INSTALANDO SERVIÇO BOXNET REPORT J&F"
echo "=========================================="

# Verificar se está rodando como root
if [[ $EUID -ne 0 ]]; then
   echo "Este script deve ser executado como root (use sudo)"
   exit 1
fi

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "ERRO: Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERRO: Docker Compose não encontrado. Instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se o diretório do projeto existe
echo "Verificando estrutura do projeto..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "  ℹ️  Diretório do projeto '$PROJECT_DIR' será criado durante a instalação."
elif [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
    echo "  ⚠️  AVISO: Arquivo docker-compose.yml não encontrado em '$PROJECT_DIR'."
    echo "     Certifique-se de adicionar o docker-compose.yml antes de usar o serviço."
fi

# Criar todos os diretórios necessários
echo "Criando diretórios necessários..."

# Diretório de logs principal
echo "  - Criando diretório de logs: $LOG_DIR"
mkdir -p "$LOG_DIR"
chmod 755 "$LOG_DIR"

# Diretório do projeto (se não existir)
if [ ! -d "$PROJECT_DIR" ]; then
    echo "  - Criando diretório do projeto: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    chmod 755 "$PROJECT_DIR"
    
    # Se o usuário boxadmin existir, dar ownership a ele
    if id "boxadmin" &>/dev/null; then
        chown boxadmin:boxadmin "$PROJECT_DIR"
        echo "    * Ownership definido para boxadmin:boxadmin"
    fi
fi

# Diretório base de dados (se especificado)
DATA_BASE_DIR="/mnt/datasense-data"
if [ ! -d "$DATA_BASE_DIR" ]; then
    echo "  - Criando diretório base de dados: $DATA_BASE_DIR"
    mkdir -p "$DATA_BASE_DIR"
    chmod 755 "$DATA_BASE_DIR"
fi

# Diretório específico para dados do J&F
JF_DATA_DIR="/mnt/datasense-data/containers/boxnet-report-jf"
if [ ! -d "$JF_DATA_DIR" ]; then
    echo "  - Criando diretório de dados J&F: $JF_DATA_DIR"
    mkdir -p "$JF_DATA_DIR"
    chmod 755 "$JF_DATA_DIR"
fi

# Subdiretórios úteis dentro do projeto
SUBDIRS=("data" "output" "temp" "config")
for subdir in "${SUBDIRS[@]}"; do
    FULL_SUBDIR="$PROJECT_DIR/$subdir"
    if [ ! -d "$FULL_SUBDIR" ]; then
        echo "  - Criando subdiretório: $FULL_SUBDIR"
        mkdir -p "$FULL_SUBDIR"
        chmod 755 "$FULL_SUBDIR"
        
        # Se o usuário boxadmin existir, dar ownership a ele
        if id "boxadmin" &>/dev/null; then
            chown boxadmin:boxadmin "$FULL_SUBDIR"
        fi
    fi
done

# Copiar script principal
echo "Instalando script principal: $SCRIPT_PATH"
cp boxnet-report-jf.sh "$SCRIPT_PATH"
chmod +x "$SCRIPT_PATH"
chown root:root "$SCRIPT_PATH"

echo "  ✓ Todos os diretórios criados com sucesso"

# Parar serviços existentes se estiverem rodando
if systemctl is-active --quiet ${SERVICE_NAME}.timer 2>/dev/null; then
    echo "Parando timer existente..."
    systemctl stop ${SERVICE_NAME}.timer
fi

if systemctl is-active --quiet ${SERVICE_NAME}.service 2>/dev/null; then
    echo "Parando serviço existente..."
    systemctl stop ${SERVICE_NAME}.service
fi

# Copiar script principal
echo "Instalando script principal: $SCRIPT_PATH"
cp boxnet-report-jf.sh "$SCRIPT_PATH"
chmod +x "$SCRIPT_PATH"
chown root:root "$SCRIPT_PATH"

# Copiar arquivos systemd
echo "Instalando serviço systemd: $SERVICE_PATH"
cp boxnet-report-jf.service "$SERVICE_PATH"
chmod 644 "$SERVICE_PATH"
chown root:root "$SERVICE_PATH"

echo "Instalando timer systemd: $TIMER_PATH"
cp boxnet-report-jf.timer "$TIMER_PATH"
chmod 644 "$TIMER_PATH"
chown root:root "$TIMER_PATH"

# Recarregar systemd
echo "Recarregando systemd..."
systemctl daemon-reload

# Habilitar timer
echo "Habilitando timer..."
systemctl enable ${SERVICE_NAME}.timer

# Iniciar timer
echo "Iniciando timer..."
systemctl start ${SERVICE_NAME}.timer

echo "=========================================="
echo "INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "=========================================="

# Mostrar status
echo "Status do timer:"
systemctl status ${SERVICE_NAME}.timer --no-pager -l

echo ""
echo "Próximas execuções programadas:"
systemctl list-timers ${SERVICE_NAME}.timer --no-pager

echo ""
echo "=========================================="
echo "ESTRUTURA DE DIRETÓRIOS CRIADA:"
echo "=========================================="
echo "📁 Projeto principal: $PROJECT_DIR"
echo "   ├── data/     (dados de entrada)"
echo "   ├── output/   (resultados gerados)"
echo "   ├── temp/     (arquivos temporários)"
echo "   └── config/   (configurações)"
echo ""
echo "📁 Dados e logs: /mnt/datasense-data/containers/boxnet-report-jf"
echo "   └── logs/     (logs de execução)"
echo ""
echo "=========================================="
echo "CONFIGURAÇÃO ATUAL:"
echo "=========================================="
echo "Horário de execução: Diariamente às 03:30 (horário de Brasília)"
echo "Diretório do projeto: $PROJECT_DIR"
echo "Diretório de logs: $LOG_DIR"
echo "Retenção de logs: 30 dias"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "=========================================="
echo "1. Adicione seu docker-compose.yml em: $PROJECT_DIR/"
echo "2. Configure seus arquivos de dados em: $PROJECT_DIR/data/"
echo "3. Execute um teste: sudo systemctl start ${SERVICE_NAME}.service"
echo "4. Monitore os logs: tail -f $LOG_DIR/latest.log"
echo ""
echo "🔧 COMANDOS ÚTEIS:"
echo "=========================================="
echo "Ver status do timer:"
echo "  sudo systemctl status ${SERVICE_NAME}.timer"
echo ""
echo "Ver próximas execuções:"
echo "  sudo systemctl list-timers ${SERVICE_NAME}.timer"
echo ""
echo "Executar manualmente (teste):"
echo "  sudo systemctl start ${SERVICE_NAME}.service"
echo ""
echo "Ver logs do systemd:"
echo "  sudo journalctl -u ${SERVICE_NAME}.service -f"
echo ""
echo "Ver logs detalhados:"
echo "  tail -f $LOG_DIR/latest.log"
echo ""
echo "Monitorar logs em tempo real:"
echo "  watch -n 5 'ls -la $LOG_DIR/ | tail -10'"
echo ""
echo "Parar/Iniciar timer:"
echo "  sudo systemctl stop ${SERVICE_NAME}.timer"
echo "  sudo systemctl start ${SERVICE_NAME}.timer"
echo ""
echo "Desinstalar serviço:"
echo "  sudo systemctl disable ${SERVICE_NAME}.timer"
echo "  sudo systemctl stop ${SERVICE_NAME}.timer"
echo "  sudo rm $SCRIPT_PATH"
echo "  sudo rm $SERVICE_PATH"
echo "  sudo rm $TIMER_PATH"
echo "  sudo systemctl daemon-reload"
echo "=========================================="