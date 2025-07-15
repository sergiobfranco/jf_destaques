import pandas as pd
from agrupamento import agrupar_noticias_por_similaridade

def test_agrupar_similaridade():
    df = pd.DataFrame({
        "Conteudo": [
            "O mercado financeiro está em alta.",
            "A bolsa de valores teve alta hoje.",
            "Um novo filme estreia nos cinemas.",
            "Estreia cinematográfica atrai multidões."
        ]
    })
    df_resultado = agrupar_noticias_por_similaridade(df, eps=0.6, min_samples=1)
    assert "Cluster" in df_resultado.columns
    assert df_resultado["Cluster"].nunique() >= 1
