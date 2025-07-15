# Gera os prompts de Setor

import pandas as pd
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import DBSCAN
import numpy as np
import re # Importar re para limpeza do tema
from collections import Counter # Importar Counter para contagem de termos

def gerar_prompts_setor(df):
    # 1. Carrega os dados (todas as notícias)
    #df = pd.read_excel(arq_api_setor)
    df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

    # 2. Carrega o modelo de embeddings (ainda não usaremos para filtragem, mas pode ser útil para outras análises)
    # model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

    # 3. Identificar notícias relacionadas aos temas (usando frequência de termos) e calcular a pontuação de relevância
    temas_termos = {
        "Setor de Papel e Celulose": ["papel", "celulose", "fibra", "eucalipto", "pulp", "paper", "cellulose"],
        "Setor de Mineração": ["mineração", "mineradora", "minério", "ferro", "níquel", "ouro", "metal", "geologia", "jazida", "mina", "mining"],
        "Setor de Agronegócios": ["agronegócio", "agro", "pecuária", "lavoura", "safra", "colheita", "grãos", "soja", "milho", "carne", "laranjas", \
                                "exportação agrícola", "rural", "agribusiness", "gripe aviária", "avícolas", "derivados", "frango", "ovos", \
                                "cacau", "crédito rural", "h5n1", "rastreabilidade", "tecnologia agrícola", "inovação agrícola", "caprinos", \
                                "ovinos", "abpa"],
        "Setor de Educação": ["educação", "escola", "universidade", "ensino", "aluno", "professor", "faculdade", "curso", "vestibular", \
                            "enem", "educacional", "estudante", "estudantes", "vestibulares", "educacional", "educacionais", "docente", \
                            "aprendizagem", "ead", "mec"],
        "Setor de Energia": ["energia", "elétrica", "usina", "hidrelétrica", "termelétrica", "eólica", "solar", "transmissão", "distribuição", \
                            "gasolina", "diesel", "etanol", "combustível", "petróleo", "gás", "conta de luz", "mme"],
        "Setor de Finanças": ["finanças", "banco", "crédito", "investimento", "investimentos", "mercado financeiro", "mercados", "ação", "renda fixa", \
                            "câmbio", "dívida", "lucro", "capital", "IPO", "banco central", "política monetária", "política econômica", "governo", \
                            "ações", "fundos", "balanço", "balanços", "bolsa", "nasdaq", "etf", "tributação", "contribuinte", "selic", "juros", \
                            "precatórios", "inflação", "deficit fiscal", "ibs", "cbs", "ibovespa", "b3", "iof"],
        "Setor de Óleo de Gás": ["óleo", "gás", "petróleo", "exploração", "refinaria", "gasoduto", "poço", "onshore", "offshore", \
                                "glp", "petrobras", "anp"],
        "Justiça": ["justiça", "judiciário", "tribunal", "juiz", "ministério público", "processo", "sentença", "condenação", "advogado", \
                    "lei", "legal", "stf", "supremo", "pena", "penas", "jurisprudência", "pgr", "julgamento", "recurso", "judicial", \
                    "denúncia", "acusação", "stj", "cnj", "golpe de estado", "penduricalhos", "agu", "alexandre de moraes"],
        "Meio Ambiente e ESG": ["meio ambiente", "sustentabilidade", "ambiental", "ambientalistas", "ecologia", "desmatamento", \
                                "poluição", "clima", "ESG", "governança ambiental", "responsabilidade social", "emissão de carbono", \
                                "biodiversidade", "amazônia", "floresta", "exploração", "cerrado", "mata atlântica", "cop30", \
                                "licenciamento ambiental", "créditos de carbono", "ibama"],
        "Política - Governo e Congresso Nacional": ["política", "governo", "congresso", "eleição", "eleições", "reeleição", "partido", "partidos", \
                                                    "ministro", "ministra", "presidente", "ex-presidente", "senado", "câmara", "deputado", "deputada", \
                                                    "senador", "senadora", "urnas", "executivo", "legislativo", "tse", "planalto", "primeira-dama", \
                                                    "casa civil", "inss", "fraude", "cpmi", "trama golpista"],
        "Setor de Esportes": ["esporte", "futebol", "basquete", "vôlei", "atletismo", "olimpíadas", "copa", "campeonato", "clube", "jogador", \
                            "treinador", "partida", "competição", "cbf", "federação", "federações", "clubes", "atleta", "atletas", \
                            "arbitragem", "fifa", "xaud", "ednaldo"] # Novo setor adicionado
    }

    # Definir os IDs dos veículos prioritários
    veiculos_prioritarios = [10459, 675]
    pontuacao_extra_veiculo = 100 # Pontuação extra para notícias desses veículos (ajuste este valor se necessário)

    def calculate_relevance_score(text, id_veiculo, temas_termos, veiculos_prioritarios, pontuacao_extra_veiculo):
        """
        Calcula uma pontuação de relevância para a notícia.
        A pontuação é baseada na frequência dos termos chave dos temas, no tamanho do texto
        e em uma pontuação extra para veículos prioritários.
        Retorna a pontuação de relevância e o tema preponderante.
        """
        text_lower = text.lower()
        theme_counts = Counter()
        total_term_count = 0

        for tema, termos in temas_termos.items():
            for termo in termos:
                count = len(re.findall(r'\b' + re.escape(termo) + r'\b', text_lower))
                theme_counts[tema] += count
                total_term_count += count

        # Remover temas com contagem zero para identificar o tema preponderante
        theme_counts_filtered = {tema: count for tema, count in theme_counts.items() if count > 0}

        preponderant_theme = None
        if theme_counts_filtered:
            preponderant_theme = max(theme_counts_filtered, key=theme_counts_filtered.get)

        # Calcular o tamanho do texto (número de palavras)
        text_size = len(text.split())

        # Calcular a pontuação do veículo
        pontuacao_veiculo = pontuacao_extra_veiculo if id_veiculo in veiculos_prioritarios else 0

        # Calcular a pontuação total de relevância
        # Podemos simplesmente somar a contagem total de termos, o tamanho do texto e a pontuação do veículo.
        # A relação exata entre esses fatores pode ser ajustada se necessário.

        # Removi temporariamente o text_size e pontuacao_veiculo
        #relevance_score = total_term_count + text_size + pontuacao_veiculo

        relevance_score = total_term_count

        return relevance_score, preponderant_theme

    # Aplicar a função para calcular a pontuação e identificar o tema preponderante
    results = df.apply(lambda row: calculate_relevance_score(row['TextoCompleto'], row['IdVeiculo'], temas_termos, veiculos_prioritarios, pontuacao_extra_veiculo), axis=1)

    # Separar os resultados em novas colunas
    df['RelevanceScore'], df['TemaPreponderante'] = zip(*results)

    # Identificar notícias do 'Setor de Esportes'
    df_esportes = df[df['TemaPreponderante'] == 'Setor de Esportes'].copy()

    # Filtrar o DataFrame para remover notícias do 'Setor de Esportes' E notícias sem tema
    df_relevante = df[
        (df['TemaPreponderante'] != 'Setor de Esportes') &  # Remove Setor de Esportes
        (df['TemaPreponderante'].notna())                 # Remove notícias sem tema
    ].copy()

    print("Número de notícias antes da filtragem: ", len(df))
    print(f"Número de notícias do Setor de Esportes removidas: {len(df_esportes)}")
    print("Número de notícias após a filtragem: ", len(df_relevante))

    # Definir os temas prioritários e a quantidade de notícias a serem selecionadas de cada um
    temas_prioritarios = {
        "Política - Governo e Congresso Nacional": 8,
        "Setor de Finanças": 7,
        "Justiça": 5,
        "Setor de Agronegócios": 5
    }

    df_top_noticias_list = []

    # Selecionar as top notícias dos temas prioritários
    for tema, qtd in temas_prioritarios.items():
        df_tema = df_relevante[df_relevante['TemaPreponderante'] == tema].sort_values(by='RelevanceScore', ascending=False)
        df_top_noticias_list.append(df_tema.head(qtd))

    # Filtrar os temas restantes
    temas_restantes = [tema for tema in df_relevante['TemaPreponderante'].unique() if tema not in temas_prioritarios]
    df_restantes = df_relevante[df_relevante['TemaPreponderante'].isin(temas_restantes)].copy()

    # Selecionar as top 7 notícias dos temas restantes
    if not df_restantes.empty:
        df_restantes_sorted = df_restantes.sort_values(by='RelevanceScore', ascending=False)
        df_top_noticias_list.append(df_restantes_sorted.head(7))

    # Concatenar todos os DataFrames das notícias selecionadas
    df_top_noticias = pd.concat(df_top_noticias_list, ignore_index=True)

    # 6. Criar prompts para cada notícia selecionada
    prompts = []
    for index, row in df_top_noticias.iterrows():
        texto_noticia = row['TextoCompleto']
        tema_preponderante = row['TemaPreponderante']
        ids_noticia = str(row['Id']) # ID da notícia
        relevance_score = row['RelevanceScore'] # Obter a pontuação de relevância
        id_veiculo_noticia = row['IdVeiculo'] # Obter o IdVeiculo da notícia

        # Criar o prompt
        corpo = texto_noticia
        prompt = (
            f"Resuma a notícia abaixo em no máximo 90 palavras. "
            f"O resumo deve focar nos aspectos relacionados ao tema de {tema_preponderante}:\n\n"
            f"{corpo}"
        )

        prompts.append({
            "Ids": ids_noticia,
            "Tipo": "Notícia Individual",
            "Prompt": prompt,
            "Tema": tema_preponderante, # Adicionar coluna de Tema Preponderante
            "RelevanceScore": relevance_score, # Adicionar a pontuação de relevância
            "IdVeiculo": id_veiculo_noticia # Adicionar o IdVeiculo
        })

    # 7. Salva em Excel
    df_prompts = pd.DataFrame(prompts)

    # Ordenar por tema para melhor organização (ou pela ordem que preferir para o arquivo de saída)
    df_prompts = df_prompts.sort_values(by='Tema')

    #df_prompts.to_excel(arq_prompts_setor, index=False)
    #print("Arquivo salvo: ", arq_prompts_setor)

    return df_prompts