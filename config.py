import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek config
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Pastas
pasta_api = "dados/api"
pasta_marca_setor = "dados/marca_setor"

# Arquivo de Favoritos gerado pela API - ORIGINAL
favoritos_marca = "Favoritos_Marcas.xlsx"
arq_api_original = os.path.join(pasta_api, favoritos_marca)
aux = "aux.xlsx"
arq_aux = os.path.join(pasta_api, aux)

favoritos_setor = "Favoritos_Setor.xlsx"
arq_api_original_setor = os.path.join(pasta_api, favoritos_setor)

favoritos_setor_inter = "Favoritos_Setor_inter.xlsx"
arq_api_original_setor_inter = os.path.join(pasta_api, favoritos_setor_inter)

favoritos_editorial = "Favoritos_Editorial.xlsx"
arq_api_original_editorial = os.path.join(pasta_api, favoritos_editorial)

favoritos_SPECIALS = "Favoritos_SPECIALS.xlsx"
arq_api_original_SPECIALS = os.path.join(pasta_api, favoritos_SPECIALS)

# Arquivo de Favoritos gerado pela API - SMALL
favoritos_small_marca = "Favoritos_Marcas_small.xlsx"
arq_api = os.path.join(pasta_api, favoritos_small_marca)

favoritos_small_setor = "Favoritos_Setor_small.xlsx"
arq_api_setor = os.path.join(pasta_api, favoritos_small_setor)

favoritos_small_editorial = "Favoritos_Editorial_small.xlsx"
arq_api_editorial = os.path.join(pasta_api, favoritos_small_editorial)

favoritos_small_SPECIALS = "Favoritos_SPECIALS_small.xlsx"
arq_api_SPECIALS = os.path.join(pasta_api, favoritos_small_SPECIALS)

# Arquivo TXT de saída com os resumos
resumos = "resumos_marcas.txt"
arq_resumos = os.path.join(pasta_marca_setor, resumos)

# Arquivo XLSX de Notícias Similares
similares = "Grupos_Noticias_Similares.xlsx"
arq_similares = os.path.join(pasta_marca_setor, similares)

similares_setor = "Grupos_Noticias_Similares_Setor.xlsx"
arq_similares_setor = os.path.join(pasta_marca_setor, similares_setor)

# Arquivo XLSX de Prompt de Resumo
prompts = "Prompts_Resumo_Noticias.xlsx"
arq_prompts = os.path.join(pasta_marca_setor, prompts)

prompts_setor = "Prompts_Resumo_Noticias_Setor.xlsx"
arq_prompts_setor = os.path.join(pasta_marca_setor, prompts_setor)

# Arquivo XLSX de Resultados
results = "Resumos_Gerados_DeepSeek.xlsx"
arq_results = os.path.join(pasta_marca_setor, results)

results_final = "Resumos_Finais_DeepSeek.xlsx"
arq_results_final = os.path.join(pasta_marca_setor, results_final)


results_setor = "Resumos_Gerados_DeepSeek_Setor.xlsx"
arq_results_setor = os.path.join(pasta_marca_setor, results_setor)

# Arquivo DOCX de Resumos
resumo_final = "Resumo_Marcas.docx"
arq_resumo_final = os.path.join(pasta_marca_setor, resumo_final)

resumo_final_ajustado = "Resumo_Marcas_ajustado.docx"
arq_resumo_final_ajustado = os.path.join(pasta_marca_setor, resumo_final_ajustado)

# Marcas
w_marcas = ['Holding', 'J&F', 'JBS', 'Joesley Batista', 'Wesley Batista', 'Júnior Friboi', 'J&F Mineração/LHG', 'J&F Mineração/LHG Mining', \
            'Banco Original', 'PicPay', 'Eldorado', 'Flora', 'Âmbar Energia', 'Ambar Energia', \
            'Canal Rural', 'Braskem', 'Instituto J&F' ]
marcas_a_ignorar = ['J&F', 'JBS', 'Joesley Batista', 'Wesley Batista', 'Júnior Friboi', 'J&F Mineração/LHG', 'J&F Mineração/LHG Mining', \
                    'Banco Original', 'PicPay', 'Eldorado', 'Flora', 'Âmbar Energia', 'Ambar Energia', \
                    'Canal Rural', 'Braskem', 'Instituto J&F' ]
# Marcas que vêm em primeiro e segundo lugar no relatório
marca1 = 'J&F'
marca2 = 'JBS'
