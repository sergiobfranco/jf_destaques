import pytest
from documentos import limpar_texto

@pytest.mark.parametrize("entrada,esperado", [
    ("**Resumo:** Este é um texto com (160 palavras)*", "Este é um texto com"),
    ("*Resumo:*
Texto relevante (90 palavras)", "Texto relevante"),
    ("**Resumo (90 palavras):** Algo útil aqui", "Algo útil aqui"),
    ("Texto limpo sem nada especial", "Texto limpo sem nada especial"),
])
def test_limpar_texto(entrada, esperado):
    assert limpar_texto(entrada) == esperado
