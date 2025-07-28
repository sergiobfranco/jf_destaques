arquivo_saida = r'dados\marca_setor\Destaques do dia - J&F_20250723_191939.docx'
import os

# Copiar para o Google Drive
pasta_drive = r'G:\Meu Drive\JF\Destaques do dia'  # Altere para o caminho da sua pasta do Drive

if not os.path.isfile(arquivo_saida):
    print(f"❌ Arquivo de saída não encontrado: {arquivo_saida}")
elif not os.path.isdir(pasta_drive):
    print(f"⚠️ Pasta do Google Drive não encontrada: {pasta_drive}")
else:
    import shutil
    destino_drive = os.path.join(pasta_drive, os.path.basename(arquivo_saida))
    shutil.copy2(arquivo_saida, destino_drive)
    print(f"📁 Arquivo também salvo em: {destino_drive}")