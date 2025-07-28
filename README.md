# Instruções para instalação em máquinas de usuários
## Criação de Chave para acesso à API do DeepSeek
- Para cada novo usuário criar uma chave exclusiva no painel do DeepSeek (https://platform.deepseek.com/api_keys)
- Criar uma linha no arquivo .env com o prefixo "DEEPSEEK_API_KEY_" mais a identificação do usuário, por exemplo: "DEEPSEEK_API_KEY_JF_RAQUEL". Neste exemplo está sendo definida uma chave para a usuária chamada RAQUEL que atende o cliente J&F. Não existe um padrão para o complemento, no entanto, **o mesmo complemento deverá ser incluído no campo perfil do arquivo de inicialização ***config_usuario.ini***, conforme detalhado abaixo**
## Estrutura de pastas
- Renomear o main.exe para JF_Destaques.exe
- Copiar a pasta **dados** para a mesma pasta onde fica o executável (\dist)
- Copiar o arquivo .env para a mesma pasta onde vai ficar o JF_Destaques.exe.
### **ATENÇÃO:** se o arquivo .env for baixado do Google Drive, o download remove o ponto inicial, e o arquivo precisa ter o nome de ".env".
## Arquivo de inicialização
- Editar o arquivo de inicialização \dados\config\config_usuario.ini
- Preencher o identificador perfil **exatamente com o complemento que foi criado no arquivo .env após o prefixo "DEEPSEEK_API_KEY_"**.
## Geração de executável
rmdir /s /q build
rmdir /s /q dist
pyinstaller --onefile --hidden-import=pyshorteners --hidden-import=pyshorteners.shorteners --hidden-import=pyshorteners.shorteners.tinyurl main.py
# Comandos git
- git add .
- git add nome_do_arquivo.py
- git commit -m "Mensagem descritiva do que você fez"
- git push
