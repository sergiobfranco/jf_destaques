import os
import re
import shutil
from annotated_types import doc
from docx import Document
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from datetime import datetime
from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn


# Função para upload no Google Drive
def upload_para_google_drive(caminho_arquivo, nome_arquivo, pasta_id):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    SERVICE_ACCOUNT_FILE = 'service_account.json'
    SCOPES = ['https://www.googleapis.com/auth/drive']

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': nome_arquivo,
        'parents': [pasta_id]
    }

    media = MediaFileUpload(caminho_arquivo, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True  # ✅ ESSENCIAL para pastas compartilhadas
    ).execute()

    print(f"✅ Upload concluído com ID: {uploaded_file.get('id')}")



def adicionar_hyperlink(paragraph, url, texto_display):
    """
    Adiciona um hyperlink a um parágrafo no documento Word
    """
    # Criar o elemento hyperlink
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), paragraph.part.relate_to(url,
                                                       "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                                                       is_external=True))

    # Criar o run com o texto do link
    new_run = OxmlElement('w:r')

    # Configurar propriedades do texto (cor azul, sublinhado)
    rPr = OxmlElement('w:rPr')

    # Cor azul
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '0000FF')
    rPr.append(color)

    # Sublinhado
    underline = OxmlElement('w:u')
    underline.set(qn('w:val'), 'single')
    rPr.append(underline)

    new_run.append(rPr)

    # Adicionar o texto
    new_run.text = texto_display
    hyperlink.append(new_run)

    return hyperlink

def processar_urls_em_paragrafo(paragraph):
    """
    Processa um parágrafo, convertendo URLs em hyperlinks
    """
    texto_completo = paragraph.text

    # REGEX CORRIGIDA - Captura URLs completas incluindo parâmetros, fragmentos, etc.
    # Esta regex é mais robusta e captura URLs até encontrar espaço ou fim de linha
    padrao_url = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?)]'

    # Alternativa ainda mais simples e eficaz:
    # padrao_url = r'https?://\S+'

    urls_encontradas = re.findall(padrao_url, texto_completo)

    # Remover URLs duplicadas mantendo a ordem
    urls_unicas = []
    for url in urls_encontradas:
        if url not in urls_unicas:
            urls_unicas.append(url)

    if urls_unicas:
        print(f"   🔗 Encontradas {len(urls_unicas)} URLs: {urls_unicas[:2]}{'...' if len(urls_unicas) > 2 else ''}")

        # Limpar o parágrafo atual
        paragraph.clear()

        # Dividir o texto pelas URLs
        texto_restante = texto_completo

        for url in urls_unicas:
            # Encontrar a posição da URL no texto
            if url in texto_restante:
                partes = texto_restante.split(url, 1)

                if len(partes) == 2:
                    # Adicionar texto antes da URL
                    if partes[0]:
                        paragraph.add_run(partes[0])

                    # Adicionar hyperlink
                    hyperlink_element = adicionar_hyperlink(paragraph, url, url)
                    paragraph._p.append(hyperlink_element)

                    # Continuar com o resto do texto
                    texto_restante = partes[1]

        # Adicionar texto restante após a última URL
        if texto_restante:
            paragraph.add_run(texto_restante)

        return True

    return False



def converter_urls_docx_para_hyperlinks(arquivo_entrada, pasta_destino='/app/output', pasta_id_drive=None):
    # 1️⃣ Validar se o arquivo existe
    if not os.path.exists(arquivo_entrada):
        print(f"❌ Erro: Arquivo '{arquivo_entrada}' não encontrado!")
        return False

    print(f"📖 Abrindo arquivo: {arquivo_entrada}")
    doc = Document(arquivo_entrada)

    # 2️⃣ Regex para encontrar URLs
    regex_url = r'(https?://[^\s]+)'
    for p in doc.paragraphs:
        if p.text.strip():
            processar_urls_em_paragrafo(p)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text.strip():
                        processar_urls_em_paragrafo(p)

    # 3️⃣ Gerar nome do arquivo final
    nome_base = os.path.basename(arquivo_entrada).replace('.docx', '')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    arquivo_saida = os.path.join('output', f"{nome_base}_{timestamp}.docx")

    # 4️⃣ Salvar primeiro o arquivo localmente
    os.makedirs('output', exist_ok=True)
    doc.save(arquivo_saida)
    print(f"💾 Arquivo salvo localmente: {arquivo_saida}")

    # 5️⃣ Upload para Google Drive, se configurado
    if pasta_id_drive:
        upload_para_google_drive(arquivo_saida, os.path.basename(arquivo_saida), pasta_id_drive)

    # 6️⃣ Copiar para a pasta compartilhada do Docker (opcional)
    if os.path.isdir(pasta_destino):
        destino_drive = os.path.join(pasta_destino, os.path.basename(arquivo_saida))
        shutil.copy2(arquivo_saida, destino_drive)
        print(f"📂 Arquivo também copiado para pasta compartilhada: {destino_drive}")
    else:
        print(f"⚠️ Pasta destino '{pasta_destino}' não encontrada. Pulei a cópia local.")

    return True


def metodo_alternativo_melhorado(arquivo_entrada, arquivo_saida):
    """
    Método alternativo melhorado - substitui URLs por texto com formatação
    """
    try:
        print(f"📖 Método alternativo melhorado - Abrindo arquivo: {arquivo_entrada}")
        doc = Document(arquivo_entrada)

        total_urls_encontradas = 0
        paragrafos_processados = 0

        # Regex melhorada para capturar URLs completas
        padrao_url = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?)]'

        # Processar parágrafos
        for paragraph in doc.paragraphs:
            if not paragraph.text.strip():
                continue

            texto_original = paragraph.text
            urls_no_texto = re.findall(padrao_url, texto_original)

            if urls_no_texto:
                print(f"   🔗 Parágrafo {paragrafos_processados + 1}: {len(urls_no_texto)} URLs encontradas")
                total_urls_encontradas += len(urls_no_texto)

                # Limpar o parágrafo
                paragraph.clear()

                # Reconstruir o parágrafo com formatação
                texto_restante = texto_original

                for url in urls_no_texto:
                    if url in texto_restante:
                        # Dividir o texto pela URL
                        partes = texto_restante.split(url, 1)
                        if len(partes) == 2:
                            # Adicionar texto antes da URL
                            if partes[0]:
                                paragraph.add_run(partes[0])

                            # Adicionar URL com formatação especial
                            run_url = paragraph.add_run(url)
                            run_url.font.color.rgb = RGBColor(0, 0, 255)  # Azul
                            run_url.underline = True

                            # Continuar com o resto
                            texto_restante = partes[1]

                # Adicionar texto restante
                if texto_restante:
                    paragraph.add_run(texto_restante)

            paragrafos_processados += 1

        # Processar tabelas também
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if not paragraph.text.strip():
                            continue

                        texto_original = paragraph.text
                        urls_no_texto = re.findall(padrao_url, texto_original)

                        if urls_no_texto:
                            total_urls_encontradas += len(urls_no_texto)
                            paragraph.clear()

                            texto_restante = texto_original
                            for url in urls_no_texto:
                                if url in texto_restante:
                                    partes = texto_restante.split(url, 1)
                                    if len(partes) == 2:
                                        if partes[0]:
                                            paragraph.add_run(partes[0])

                                        run_url = paragraph.add_run(url)
                                        run_url.font.color.rgb = RGBColor(0, 0, 255)
                                        run_url.underline = True

                                        texto_restante = partes[1]

                            if texto_restante:
                                paragraph.add_run(texto_restante)

        # Salvar documento
        arquivo_local = arquivo_saida
        nome_arquivo = os.path.basename(arquivo_saida)
        upload_para_google_drive(arquivo_local, nome_arquivo, "1HCo8W9Q9ak8aKOmMRPhSyVBntCS_GD6J")        
        doc.save(arquivo_saida)

        # Copiar para o Google Drive
        pasta_drive = r'/app/relatorios/'  # Altere para o caminho da sua pasta do Drive
        if os.path.isdir(pasta_drive):
            import shutil
            destino_drive = os.path.join(pasta_drive, os.path.basename(arquivo_saida))
            shutil.copy2(arquivo_saida, destino_drive)
            print(f"📁 Arquivo também salvo em: {destino_drive}")
        else:
            print(f"⚠️ Pasta do Google Drive não encontrada: {pasta_drive}")
            
        print(f"\n✅ Método alternativo concluído!")
        print(f"📊 Estatísticas:")
        print(f"   - Parágrafos processados: {paragrafos_processados}")
        print(f"   - Total de URLs formatadas: {total_urls_encontradas}")
        print(f"💾 Arquivo salvo como: {arquivo_saida}")

        return True

    except Exception as e:
        print(f"❌ Erro no método alternativo: {str(e)}")
        return False

def testar_regex():
    """
    Função para testar a regex com URLs de exemplo
    """
    print("🧪 Testando regex com URLs de exemplo...")

    # URLs de teste
    urls_teste = [
        "https://tinyurl.com/2aymnjlf",
        "https://www.google.com/search?q=python",
        "http://example.com/path/to/file.html",
        "https://github.com/user/repo#readme",
        "https://site.com/page?param1=value1&param2=value2"
    ]

    # Regex melhorada
    padrao_url = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?)]'

    for url in urls_teste:
        match = re.search(padrao_url, url)
        if match:
            print(f"   ✅ {url} -> Capturado: {match.group()}")
        else:
            print(f"   ❌ {url} -> Não capturado")

    print("\n" + "="*50)

def gerar_versao_ajustada(arquivo_preliminar, pasta_id_drive=None):
    """
    Aplica os ajustes finais ao relatório:
    - Converte URLs em hyperlinks
    - Gera nome do arquivo com timestamp
    - Salva localmente e realiza upload para o Google Drive (se configurado)
    """

    if not os.path.exists(arquivo_preliminar):
        print(f"❌ Arquivo não encontrado: {arquivo_preliminar}")
        return

    print(f"📖 Aplicando versão ajustada com hyperlinks e timestamp...")
    
    # 🧠 Reaproveitar função que já processa os hyperlinks e salva com timestamp
    sucesso = converter_urls_docx_para_hyperlinks(arquivo_preliminar, pasta_id_drive=pasta_id_drive)

    if sucesso:
        print("✅ Versão final ajustada com sucesso.")
    else:
        print("❌ Falha ao gerar a versão ajustada.")
