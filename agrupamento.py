from sklearn.cluster import DBSCAN
from sentence_transformers import SentenceTransformer
import pandas as pd

def agrupar_noticias_por_similaridade(df, campo_texto='Conteudo', eps=0.5, min_samples=2):
    modelo = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    textos = df[campo_texto].fillna("").tolist()
    embeddings = modelo.encode(textos)

    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine').fit(embeddings)
    df['Cluster'] = clustering.labels_
    return df
