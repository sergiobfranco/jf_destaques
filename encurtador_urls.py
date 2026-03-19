# ============================================================================
# SISTEMA OTIMIZADO DE ENCURTAMENTO DE URLs
# ============================================================================
# Arquivo: encurtador_urls.py
# Autor: Sistema de Relatórios J&F
# Descrição: Sistema robusto de encurtamento com cache e múltiplos fallbacks
# ============================================================================

import requests
import time
import pandas as pd
from urllib.parse import quote
import json
import os
from datetime import datetime


# ============================================================================
# FUNÇÕES DE ENCURTAMENTO POR SERVIÇO
# ============================================================================

def encurtar_com_vgd(url):
    """
    v.gd - Clone estável do is.gd
    ✅ SEM LIMITES
    ✅ SEM TELAS INTERMEDIÁRIAS
    ✅ ALTA CONFIABILIDADE
    """
    try:
        api_url = f"https://v.gd/create.php?format=simple&url={quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text.strip(), "v.gd"
        return None, f"v.gd retornou: {response.text[:50]}"
    except Exception as e:
        return None, f"v.gd falhou: {str(e)[:50]}"


def encurtar_com_clckru(url):
    """
    clck.ru - Serviço russo
    ✅ SEM LIMITES
    ✅ SEM TELAS INTERMEDIÁRIAS
    ✅ MUITO RÁPIDO
    """
    try:
        api_url = f"https://clck.ru/--?url={quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text.strip(), "clck.ru"
        return None, f"clck.ru retornou: {response.text[:50]}"
    except Exception as e:
        return None, f"clck.ru falhou: {str(e)[:50]}"


def encurtar_com_dagd(url):
    """
    da.gd - Serviço minimalista
    ✅ SEM LIMITES
    ✅ SEM TELAS INTERMEDIÁRIAS
    ✅ SIMPLES E DIRETO
    """
    try:
        api_url = f"https://da.gd/s?url={quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and 'da.gd' in response.text:
            return response.text.strip(), "da.gd"
        return None, f"da.gd retornou: {response.text[:50]}"
    except Exception as e:
        return None, f"da.gd falhou: {str(e)[:50]}"


def encurtar_com_ulvis(url):
    """
    ulvis.net - Backup confiável
    ⚠️  LIMITE: ~500 URLs/dia
    ✅ SEM TELAS INTERMEDIÁRIAS
    """
    try:
        api_url = "https://ulvis.net/api.php"
        params = {'url': url}
        response = requests.post(api_url, data=params, timeout=10)
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text.strip(), "ulvis.net"
        return None, f"ulvis.net retornou: {response.text[:50]}"
    except Exception as e:
        return None, f"ulvis.net falhou: {str(e)[:50]}"


def encurtar_com_isgd(url):
    """
    is.gd - Serviço original (mantido como último recurso)
    ✅ SEM LIMITES (quando funciona)
    ⚠️  INSTÁVEL (frequentemente fora do ar)
    """
    try:
        api_url = f"https://is.gd/create.php?format=simple&url={quote(url)}"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text.strip(), "is.gd"
        return None, f"is.gd retornou: {response.text[:50]}"
    except Exception as e:
        return None, f"is.gd falhou: {str(e)[:50]}"


# ============================================================================
# VALIDAÇÃO DE URLs
# ============================================================================

def validar_url(url):
    """
    Valida se a URL está em formato correto antes de tentar encurtar
    """
    if not url or pd.isna(url):
        return False, "URL vazia ou None"
    
    url_str = str(url).strip()
    
    # Lista de valores inválidos
    valores_invalidos = [
        '', 'nan', 'None', 'null',
        'URL Não Disponível', 
        'URL NÃ£o DisponÃ­vel',
        'URL não disponível'
    ]
    
    if not url_str or url_str in valores_invalidos:
        return False, "URL inválida ou placeholder"
    
    if not url_str.startswith(('http://', 'https://')):
        return False, "URL sem protocolo HTTP/HTTPS"
    
    return True, "URL válida"


# ============================================================================
# FUNÇÃO BÁSICA DE ENCURTAMENTO (sem cache)
# ============================================================================

def encurtar_url_seguro(url_original, max_tentativas_por_servico=2, delay=1):
    """
    Encurta URL com fallback automático entre múltiplos serviços
    
    ORDEM DE PRIORIDADE (SEM TELA INTERMEDIÁRIA):
    1. clck.ru   → Redirecionamento direto, rápido, ilimitado ✅
    2. da.gd     → Redirecionamento direto, estável, ilimitado ✅
    3. is.gd     → Redirecionamento direto, lento mas confiável ✅
    4. v.gd      → TEM TELA DE AVISO (último recurso) ⚠️
    5. ulvis.net → Limite de ~500 URLs/dia
    
    Args:
        url_original: URL para encurtar
        max_tentativas_por_servico: Tentativas por serviço (padrão: 2)
        delay: Segundos entre tentativas (padrão: 1)
    
    Returns:
        URL encurtada ou URL original se todos falharem
    """
    
    # Validação inicial
    url_valida, msg_validacao = validar_url(url_original)
    if not url_valida:
        print(f"⚠️  Validação falhou: {msg_validacao}")
        return str(url_original) if url_original else "URL não disponível"
    
    url_str = str(url_original).strip()
    
    # Lista de serviços em ordem de preferência
    # NOVA ORDEM: Serviços SEM tela intermediária primeiro
    servicos = [
        ("da.gd", encurtar_com_dagd),         # 1º - Aceita URLs longas, sem tela ✅
        ("is.gd", encurtar_com_isgd),         # 2º - Backup confiável
        ("clck.ru", encurtar_com_clckru),     # 3º - Para URLs curtas
        ("v.gd", encurtar_com_vgd),           # 4º - TEM TELA DE AVISO
        ("ulvis.net", encurtar_com_ulvis),    # 5º - Limite diário
    ]
    
    print(f"🔗 Encurtando: {url_str[:60]}...")
    
    # Tentar cada serviço
    for nome_servico, funcao_servico in servicos:
        for tentativa in range(max_tentativas_por_servico):
            try:
                print(f"   {nome_servico} (tent {tentativa + 1})...", end=" ")
                
                resultado, info = funcao_servico(url_str)
                
                if resultado:
                    print(f"✅")
                    return resultado
                else:
                    print(f"❌ {info[:30]}")
                    
            except Exception as e:
                print(f"❌ {str(e)[:30]}")
            
            # Aguardar antes da próxima tentativa
            if tentativa < max_tentativas_por_servico - 1:
                time.sleep(delay)
        
        # Pequena pausa entre serviços diferentes
        time.sleep(0.3)
    
    # Se todos falharam, retornar URL original
    print(f"⚠️  Todos falharam. Usando URL original.")
    return url_str


# ============================================================================
# GERENCIADOR DE URLs COM CACHE
# ============================================================================

class GerenciadorURLs:
    """
    Gerencia cache de URLs encurtadas para evitar reprocessamento
    
    BENEFÍCIOS:
    - Reduz ~60-80% das requisições (URLs repetidas)
    - Acelera processamento
    - Evita atingir limites de serviços
    - Mantém histórico de URLs processadas
    """
    
    def __init__(self, arquivo_cache='dados/cache_urls.json'):
        """
        Inicializa o gerenciador de URLs
        
        Args:
            arquivo_cache: Caminho do arquivo JSON de cache
        """
        self.arquivo_cache = arquivo_cache
        self.cache = self._carregar_cache()
        self.estatisticas_sessao = {
            'cache_hits': 0,
            'novas_urls': 0,
            'falhas': 0
        }
    
    def _carregar_cache(self):
        """Carrega cache existente do disco"""
        if os.path.exists(self.arquivo_cache):
            try:
                with open(self.arquivo_cache, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    print(f"📦 Cache carregado: {len(cache)} URLs")
                    return cache
            except Exception as e:
                print(f"⚠️  Erro ao carregar cache: {e}")
                return {}
        else:
            print(f"📦 Cache novo criado")
            return {}
    
    def _salvar_cache(self):
        """Salva cache em disco"""
        try:
            # Criar diretório se não existir
            dir_cache = os.path.dirname(self.arquivo_cache)
            if dir_cache and not os.path.exists(dir_cache):
                os.makedirs(dir_cache, exist_ok=True)
            
            with open(self.arquivo_cache, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"⚠️  Erro ao salvar cache: {e}")
    
    def obter_url_curta(self, url_original, salvar_cache_automatico=True):
        """
        Retorna URL curta do cache ou encurta nova URL
        
        Args:
            url_original: URL para encurtar
            salvar_cache_automatico: Se True, salva cache após cada nova URL
        
        Returns:
            URL encurtada ou original se falhar
        """
        # Normalizar URL
        url_normalizada = str(url_original).strip() if url_original else ""
        
        # Verificar se já existe no cache
        if url_normalizada in self.cache:
            self.estatisticas_sessao['cache_hits'] += 1
            dados_cache = self.cache[url_normalizada]
            print(f"📦 Cache HIT: {dados_cache['url_curta']}")
            return dados_cache['url_curta']
        
        # Encurtar nova URL
        print(f"🆕 Nova URL")
        url_curta = encurtar_url_seguro(url_normalizada)
        
        # Verificar se encurtamento foi bem-sucedido
        if url_curta == url_normalizada:
            self.estatisticas_sessao['falhas'] += 1
        else:
            self.estatisticas_sessao['novas_urls'] += 1
        
        # Salvar no cache
        self.cache[url_normalizada] = {
            'url_curta': url_curta,
            'data': datetime.now().isoformat(),
            'servico': self._detectar_servico(url_curta),
            'url_original_length': len(url_normalizada),
            'url_curta_length': len(url_curta)
        }
        
        # Salvar cache automaticamente
        if salvar_cache_automatico:
            self._salvar_cache()
        
        return url_curta
    
    def _detectar_servico(self, url_curta):
        """Detecta qual serviço foi usado"""
        if not url_curta:
            return 'falha'
        
        url_lower = url_curta.lower()
        
        if 'v.gd' in url_lower:
            return 'v.gd'
        elif 'clck.ru' in url_lower:
            return 'clck.ru'
        elif 'da.gd' in url_lower:
            return 'da.gd'
        elif 'ulvis.net' in url_lower:
            return 'ulvis.net'
        elif 'is.gd' in url_lower:
            return 'is.gd'
        else:
            return 'original'
    
    def estatisticas(self):
        """Exibe estatísticas do cache"""
        total = len(self.cache)
        por_servico = {}
        
        for dados in self.cache.values():
            servico = dados.get('servico', 'desconhecido')
            por_servico[servico] = por_servico.get(servico, 0) + 1
        
        print("\n" + "="*80)
        print("📊 ESTATÍSTICAS DO CACHE DE URLs")
        print("="*80)
        print(f"📦 Total em cache: {total}")
        print(f"✅ Cache hits: {self.estatisticas_sessao['cache_hits']}")
        print(f"🆕 Novas URLs: {self.estatisticas_sessao['novas_urls']}")
        print(f"❌ Falhas: {self.estatisticas_sessao['falhas']}")
        
        total_processado = self.estatisticas_sessao['cache_hits'] + self.estatisticas_sessao['novas_urls']
        if total_processado > 0:
            taxa = (self.estatisticas_sessao['cache_hits'] / total_processado * 100)
            print(f"📊 Taxa de reuso: {taxa:.1f}%")
        
        if por_servico:
            print(f"\n🔧 Por serviço:")
            for servico, count in sorted(por_servico.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total * 100) if total > 0 else 0
                print(f"   {servico:12} → {count:4} ({pct:5.1f}%)")
        
        print("="*80 + "\n")


# ============================================================================
# FUNÇÕES DE TESTE E DIAGNÓSTICO
# ============================================================================

def testar_servicos_encurtamento():
    """
    Testa todos os serviços de encurtamento
    Retorna número de serviços funcionando
    """
    print("\n" + "="*80)
    print("🔬 TESTE DE SERVIÇOS DE ENCURTAMENTO")
    print("="*80)
    
    url_teste = "https://www.google.com/search?q=teste"
    
    servicos = [
        ("v.gd", encurtar_com_vgd),
        ("clck.ru", encurtar_com_clckru),
        ("da.gd", encurtar_com_dagd),
        ("ulvis.net", encurtar_com_ulvis),
        ("is.gd", encurtar_com_isgd),
    ]
    
    resultados = []
    
    for nome, funcao in servicos:
        print(f"🧪 {nome}...", end=" ")
        try:
            resultado, info = funcao(url_teste)
            
            if resultado:
                print(f"✅ OK → {resultado}")
                resultados.append((nome, "OK"))
            else:
                print(f"❌ Falhou")
                resultados.append((nome, "FALHOU"))
        except Exception as e:
            print(f"❌ Erro: {str(e)[:40]}")
            resultados.append((nome, "ERRO"))
        
        time.sleep(0.5)
    
    servicos_ok = sum(1 for _, s in resultados if s == "OK")
    
    print("="*80)
    print(f"📈 RESULTADO: {servicos_ok}/{len(servicos)} funcionando")
    
    if servicos_ok == 0:
        print("⚠️  ALERTA: Nenhum serviço disponível!")
    elif servicos_ok < 3:
        print("⚠️  AVISO: Poucos serviços disponíveis")
    else:
        print("✅ OK para processamento")
    
    print("="*80 + "\n")
    
    return servicos_ok


# ============================================================================
# TESTE DO MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("🚀 TESTE DO SISTEMA DE ENCURTAMENTO\n")
    
    # Testar serviços
    servicos_ok = testar_servicos_encurtamento()
    
    if servicos_ok > 0:
        # Testar gerenciador
        print("\n🧪 Testando gerenciador com cache...")
        ger = GerenciadorURLs('cache_teste.json')
        
        urls = [
            "https://www.exemplo.com/pagina1",
            "https://www.exemplo.com/pagina2",
            "https://www.exemplo.com/pagina1",  # Repetida
        ]
        
        for url in urls:
            print(f"\n{'='*60}")
            curta = ger.obter_url_curta(url)
            print(f"→ {curta}")
        
        ger.estatisticas()
    
    print("\n✅ Teste concluído!")