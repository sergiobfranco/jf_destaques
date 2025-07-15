import requests
import pandas as pd
import os

from config import API_URL_MARCAS, API_KEY

def processar_marcas(final_df):
    lista_dicts = []

    for _, row in final_df.iterrows():
        try:
            response = requests.post(
                API_URL_MARCAS,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"inputs": row["Titulo"] + " - " + row["Conteudo"]},
                timeout=30
            )
            if response.status_code == 200:
                marcas = response.json()
                lista_dicts.append({
                    "Id": row["Id"],
                    "Marcas": marcas
                })
            else:
                print(f"Erro ao consultar API para Id {row['Id']}: {response.status_code}")
        except Exception as e:
            print(f"Exceção ao consultar API para Id {row['Id']}: {str(e)}")

    return pd.DataFrame(lista_dicts)
