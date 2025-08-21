@echo off
set "HOST=boxadmin@10.1.20.25"
set "KEY=%USERPROFILE%\.ssh\id_ed25519"
set "SCRIPT=/home/boxadmin/jf-relatorio/run_cron.sh"

echo Disparando job no servidor...
ssh -i "%KEY%" %HOST% "bash -lc '%SCRIPT%'"
pause
