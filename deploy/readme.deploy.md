
# Execute a instalação:
```bash
sudo chmod +x install-boxnet-report-jf.sh
sudo ./install-boxnet-report-jf.sh
```

# Estrutura de Diretórios

📁 **Projeto principal:** `/home/boxadmin/jf-relatorio/`
```
├── data/     (dados de entrada)
├── output/   (resultados gerados)
├── temp/     (arquivos temporários)
└── config/   (configurações)
```

📁 **Dados e logs:** `/mnt/datasense-data/containers/boxnet-report-jf/`
```
└── logs/     (logs de execução)
```

# ⌛ Para alterar o schedule de 03h30AM BRT

## Parar o serviço timer:
```bash
sudo systemctl stop boxnet-report-jf.timer
```
## Desabilitar o serviço timer:
```bash
sudo systemctl disable boxnet-report-jf.timer
```
## Alterar o arquivo **boxnet-report-jf.timer** nas linhas 2 e 7 seguindo o padrão apresentado:
```yaml
[Unit]
Description=Run Boxnet J&F Report daily at 3:30 AM Brazilian Time
Requires=boxnet-report-jf.service

[Timer]
# Executa às 03:30 todos os dias (horário de Brasília)
OnCalendar=*-*-* 03:30:00
# Timezone brasileiro
Environment="TZ=America/Sao_Paulo"
# Se o sistema estiver desligado quando deveria executar, executa na próxima inicialização
Persistent=true
# Adiciona aleatoriedade de até 5 minutos para evitar sobrecarga
RandomizedDelaySec=300
# Precisão de 1 minuto
AccuracySec=1m

[Install]
WantedBy=timers.target
```

## Copiar o arquivo **boxnet-report-jf.timer** para a pasta `/etc/systemd/system` e dar permissões:
```bash
sudo cp boxnet-report-jf.timer /etc/systemd/system/boxnet-report-jf.timer

sudo chmod 644 /etc/systemd/system/boxnet-report-jf.timer

sudo chown root:root /etc/systemd/system/boxnet-report-jf.timer

```
## Reload do Daemon de serviços:
```bash
sudo systemctl daemon-reload
```
## Habilitar o serviço timer:
```bash
sudo systemctl enable boxnet-report-jf.timer
```
## Iniciar o serviço timer:
```bash
sudo systemctl start boxnet-report-jf.timer
```

# 🔍 Comandos para monitorar:

> **Nota:** Esses comandos devem ser executados no terminal do servidor Linux com permissão de administrador (`sudo`).

## Ver status do timer:
```bash
sudo systemctl status boxnet-report-jf.timer
```
## Ver próximas execuções:
```bash
sudo systemctl list-timers boxnet-report-jf.timer
```
## Executar manualmente:
```bash
sudo systemctl start boxnet-report-jf.service
```

## Ver log em tempo real (durante execução)
```bash
tail -f /mnt/datasense-data/containers/boxnet-report-jf/logs/latest.log
``` 

## Ver apenas logs do container
```bash
grep "\[DOCKER\]" /mnt/datasense-data/containers/boxnet-report-jf/logs/latest.log
```

## Ver apenas logs do sistema
```bash
grep -v "\[DOCKER\]" /mnt/datasense-data/containers/boxnet-report-jf/logs/latest.log
```

## Ver últimas 50 linhas
```bash
tail -50 /mnt/datasense-data/containers/boxnet-report-jf/logs/latest.log
```