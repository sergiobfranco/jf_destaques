# teste_producao.py
print("="*80)
print("TESTE NO AMBIENTE DE PRODUCAO")
print("="*80)

# 1. Verificar qual arquivo está sendo usado
import encurtador_urls
print(f"\n[1] Arquivo importado:")
print(f"    {encurtador_urls.__file__}")

# 2. Testar URL única
print(f"\n[2] Testando encurtamento direto:")

url_teste = "https://www.exemplo.com.br/teste123"
url_curta = encurtador_urls.encurtar_url_seguro(url_teste, max_tentativas_por_servico=1)

print(f"    URL original: {url_teste}")
print(f"    URL curta: {url_curta}")

# 3. Identificar qual serviço foi usado
if "v.gd" in url_curta:
    print("    ✅ Servico usado: v.gd (CORRETO - primeiro da lista)")
elif "clck.ru" in url_curta:
    print("    ⚠️ Servico usado: clck.ru (segundo da lista)")
elif "da.gd" in url_curta:
    print("    ⚠️ Servico usado: da.gd (terceiro da lista)")
elif "is.gd" in url_curta:
    print("    ❌ Servico usado: is.gd (ERRADO - deveria ser ultimo recurso!)")
    print("    ❌ PROBLEMA CONFIRMADO: is.gd sendo usado indevidamente")
else:
    print(f"    ⚠️ Servico desconhecido ou URL original")

# 4. Verificar GerenciadorURLs
print(f"\n[3] Testando GerenciadorURLs:")
from encurtador_urls import GerenciadorURLs

ger = GerenciadorURLs('cache_teste_prod.json')
url_curta_ger = ger.obter_url_curta("https://www.exemplo.com.br/teste456")

print(f"    URL curta: {url_curta_ger}")

if "is.gd" in url_curta_ger:
    print("    ❌ PROBLEMA: GerenciadorURLs também está usando is.gd!")

# 5. Testar cada serviço individualmente
print(f"\n[4] Testando serviços individuais:")

from encurtador_urls import (
    encurtar_com_vgd,
    encurtar_com_clckru,
    encurtar_com_dagd,
    encurtar_com_isgd
)

testes = [
    ("v.gd", encurtar_com_vgd),
    ("clck.ru", encurtar_com_clckru),
    ("da.gd", encurtar_com_dagd),
    ("is.gd", encurtar_com_isgd),
]

for nome, func in testes:
    try:
        resultado, info = func("https://www.teste.com")
        if resultado:
            print(f"    ✅ {nome}: OK - {resultado}")
        else:
            print(f"    ❌ {nome}: FALHOU - {info}")
    except Exception as e:
        print(f"    ❌ {nome}: ERRO - {str(e)[:50]}")

print("\n" + "="*80)