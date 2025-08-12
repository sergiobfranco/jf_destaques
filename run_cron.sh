#!/bin/bash
set -e

# 1) PATH mínimo pro cron achar os binários
export PATH=/usr/local/bin:/usr/bin:/bin

# 2) Vai para a pasta do projeto
cd /home/boxadmin/jf-relatorio || exit 1

# 3) Garante a pasta de logs
mkdir -p /home/boxadmin/jf-relatorio/logs

# 4) Limpa apenas imagens "dangling" (<none>) de builds antigos
/usr/bin/docker image prune -f || true

# Remove build cache antigo
/usr/bin/docker builder prune -a -f || true

# 5) Sobe os serviços em modo detached e reconstrói se necessário
/usr/bin/docker compose up --build --remove-orphans --abort-on-container-exit

# 6) Captura logs do serviço principal "relatorio"
#    Tenta pegar o container pelo nome do serviço no compose; se falhar, faz um fallback por nome
LOGFILE="/home/boxadmin/jf-relatorio/logs/jf-relatorio_$(date +%F_%H-%M-%S).log"

# dá um tempinho pro container subir
sleep 5

# tenta pegar o ID pelo serviço "relatorio"
CID=$(/usr/bin/docker compose ps -q relatorio || true)

# fallback: pega o primeiro container que contenha "relatorio" no nome
if [ -z "$CID" ]; then
  CID=$(/usr/bin/docker ps --format '{{.ID}} {{.Names}}' | grep -i 'relatorio' | head -n 1 | awk '{print $1}')
fi

if [ -n "$CID" ]; then
  # stream de logs até o container encerrar
  /usr/bin/docker logs -f "$CID" >> "$LOGFILE" 2>&1
else
  echo "Nenhum container do serviço 'relatorio' encontrado." >> "$LOGFILE"
fi
#!/bin/bash
set -e

# PATH básico pro cron
export PATH=/usr/local/bin:/usr/bin:/bin

# Paths
PROJ="/home/boxadmin/jf-relatorio"
LOGDIR="/mnt/datasense-data/jf-relatorio/logs"   # usa o disco com espaço
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/jf-relatorio_$(date +%F_%H-%M-%S).log"

cd "$PROJ" || exit 1

# Limpezas seguras (evitam encher o disco)
#/usr/bin/docker system prune -af --volumes || true   # mais agressivo (opcional)
 /usr/bin/docker image prune -f || true
 /usr/bin/docker builder prune -a -f || true

# 1) Executa o pipeline em foreground e grava tudo no LOGFILE
#    --abort-on-container-exit faz o compose parar quando o serviço principal terminar
/usr/bin/docker compose up --build --remove-orphans --abort-on-container-exit >> "$LOGFILE" 2>&1

# 2) Ao terminar, derruba os containers e redes do compose
/usr/bin/docker compose down --remove-orphans >> "$LOGFILE" 2>&1

# 3) Finalizou OK
echo "[INFO] Execução finalizada em $(date)" >> "$LOGFILE"
