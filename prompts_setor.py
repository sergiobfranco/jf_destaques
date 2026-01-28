# Gera os prompts de Setor

import pandas as pd
try:
    # Import lazily - só necessário se for instanciar o modelo de embeddings
    from sentence_transformers import SentenceTransformer, util  # type: ignore
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    _HAS_SENTENCE_TRANSFORMERS = False
from sklearn.cluster import DBSCAN
import numpy as np
import time
import re # Importar re para limpeza do tema
from collections import Counter # Importar Counter para contagem de termos
from config import arq_relevance_score_setor, lista_setores, qt_politica, qt_financas, qt_justica, qt_agro, qt_demais

def gerar_prompts_setor(df):
    start_time = time.time()
    # 1. Carrega os dados (todas as notícias)
    #df = pd.read_excel(arq_api_setor)
    df['TextoCompleto'] = df['Titulo'].fillna('') + '. ' + df['Conteudo'].fillna('')

    # 2. Carrega o modelo de embeddings (ainda não usaremos para filtragem, mas pode ser útil para outras análises)
    # Carregue o modelo somente se a biblioteca estiver disponível e você realmente precisar
    # Exemplo:
    # if _HAS_SENTENCE_TRANSFORMERS:
    #     model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    # else:
    #     model = None

    # 3. Identificar notícias relacionadas aos temas (usando frequência de termos) e calcular a pontuação de relevância
    temas_termos = {
        "Setor de Papel e Celulose": ["papel", "celulose", "fibra", "eucalipto", "pulp", "paper", "cellulose",
                             # Empresas do Setor
                             "suzano", "klabin", "eldorado brasil", "fibria", "veracel", "cenibra", \
                             "international paper", "stora enso", "cmpc", "arauco", "oji paper", \
                             "nippon paper", "mondi", "smurfit kappa", "westrock", "packaging corporation", \
                             "georgia-pacific", "resolute forest products", "canfor", "weyerhaeuser", \
                             
                             # Matérias-Primas e Espécies Florestais
                             "pinus", "acácia", "bambu", "eucalipto urograndis", "eucalipto grandis", \
                             "eucalipto saligna", "pinus elliottii", "pinus taeda", "híbridos clonais", \
                             "clones", "melhoramento genético", "biotecnologia florestal", \
                             "silvicultura", "manejo florestal", "rotação florestal", "ciclo de corte", \
                             "madeira de reflorestamento", "madeira plantada", "tora", "cavaco", \
                             "chips", "resíduo florestal", "casca", "serragem", \
                             
                             # Processos Produtivos
                             "polpação", "branqueamento", "digestão", "cozimento", "deslignificação", \
                             "kraft", "sulfato", "sulfito", "soda", "organosolv", \
                             "descascamento", "picagem", "impregnação", "lavagem", \
                             "depuração", "flotação", "espessamento", "secagem", \
                             "formação da folha", "prensagem", "calandragem", "rebobinamento", \
                             "converting", "tissue making", "coating", "laminação", \
                             
                             # Produtos de Papel e Celulose
                             "celulose branqueada", "celulose não branqueada", "celulose fluff", \
                             "polpa de fibra curta", "polpa de fibra longa", "dissolving pulp", \
                             "papel jornal", "papel imprensa", "papel offset", "papel couchê", \
                             "papel cartão", "cartolina", "papel kraft", "papel tissue", \
                             "papel higiênico", "papel toalha", "guardanapo", "lenço", \
                             "embalagem", "papelão ondulado", "papel para saco", \
                             "papel de parede", "papel filtro", "papel fotográfico", \
                             
                             # Equipamentos e Tecnologia
                             "digestor", "branqueador", "máquina de papel", "formador", \
                             "prensa", "secador", "calandra", "rebobinadeira", "pope reel", \
                             "headbox", "wire", "forming fabric", "press felt", \
                             "yankee dryer", "tad", "através de ar", "crescent former", \
                             "gap former", "multi-layer headbox", "dilution water system", \
                             
                             # Aspectos Ambientais e Sustentabilidade
                             "certificação florestal", "fsc", "pefc", "cerflor", "forest stewardship council", \
                             "programa de certificação florestal", "manejo sustentável", \
                             "plantio responsável", "conservação da biodiversidade", \
                             "corredor ecológico", "restauração florestal", "recuperação de áreas", \
                             "carbon sink", "sequestro de carbono", "neutralidade de carbono", \
                             "pegada de carbono", "pegada hídrica", "economia circular", \
                             "bioeconomia", "biorefinery", "biorrefinaria", \
                             
                             # Tratamento de Efluentes e Resíduos
                             "licor negro", "licor branco", "licor verde", "caldeira de recuperação", \
                             "forno de cal", "caustificação", "evaporação", "cristalização", \
                             "tratamento primário", "tratamento secundário", "tratamento terciário", \
                             "lagoa de sedimentação", "flotador", "clarificador", \
                             "lodo biológico", "biodigestor", "compostagem", "incineração", \
                             "aproveitamento energético", "cogeração", "biomassa", \
                             
                             # Parâmetros de Qualidade
                             "alvura", "opacidade", "gramatura", "densidade", "porosidade", \
                             "resistência", "tração", "compressão", "dobra dupla", "rasgo", \
                             "estouro", "rigidez", "formação", "rugosidade", "absorção", \
                             "printabilidade", "runnability", "smoothness", "brightness", \
                             "iso brightness", "tappi", "scan", "pfi", "kappa number", \
                             
                             # Mercado e Comercialização
                             "preço da celulose", "índice pix", "foex", "risi", "fastmarkets", \
                             "prêmio asiático", "mercado spot", "contratos de longo prazo", \
                             "fob", "cif", "exportação", "importação", "player global", \
                             "market share", "capacidade instalada", "utilization rate", \
                             "shutdown", "manutenção programada", "restart", \
                             
                             # Aspectos Logísticos
                             "porto de santos", "terminal portuário", "armazenagem", \
                             "movimentação", "embarque", "desembarque", "frete", \
                             "transporte rodoviário", "transporte ferroviário", "transporte hidroviário", \
                             "caminhão canavieiro", "vagão", "navio graneleiro", \
                             "container", "big bag", "fardo", "bobina", "resma", \
                             
                             # Regiões Produtoras
                             "são paulo", "bahia", "espírito santo", "minas gerais", \
                             "mato grosso do sul", "rio grande do sul", "paraná", \
                             "maranhão", "pará", "tocantins", "região nordeste", \
                             "região sudeste", "região sul", "interior paulista", \
                             "vale do paraíba", "extremo sul da bahia", \
                             
                             # Aspectos Econômicos e Financeiros
                             "capex", "capital expenditure", "opex", "operational expenditure", \
                             "ebitda", "margem operacional", "cash cost", "custo variável", \
                             "custo fixo", "depreciação", "amortização", "fluxo de caixa", \
                             "roi", "return on investment", "payback", "npv", "irr", \
                             "project finance", "financiamento de projeto", \
                             
                             # Inovação e Desenvolvimento
                             "i&d", "pesquisa e desenvolvimento", "inovação", "nanotecnologia", \
                             "nanocelulose", "celulose microfibrilada", "mfc", "cnf", \
                             "celulose nanocristalina", "cnc", "materiais avançados", \
                             "bioplásticos", "biomateriais", "química verde", \
                             "biotecnologia industrial", "enzimas", "bioengenharia", \
                             
                             # Energia e Utilidades
                             "energia elétrica", "vapor", "caldeira", "turbina", "gerador", \
                             "cogeração", "autossuficiência energética", "excedente elétrico", \
                             "venda de energia", "biomassa residual", "casca", "lodo", \
                             "licor negro concentrado", "power boiler", "recovery boiler", \
                             
                             # Recursos Humanos e Segurança
                             "mão de obra especializada", "treinamento", "capacitação", \
                             "segurança do trabalho", "saúde ocupacional", "acidentes", \
                             "ltif", "lost time injury frequency", "meio ambiente", \
                             "saúde e segurança", "sms", "cultura de segurança", \
                             
                             # Regulamentação e Normas
                             "iso 9001", "iso 14001", "ohsas 18001", "iso 45001", \
                             "regulamentação ambiental", "licenciamento", "outorga de água", \
                             "emissões atmosféricas", "efluentes líquidos", "resíduos sólidos", \
                             "termo de ajustamento de conduta", "compensação ambiental", \
                             
                             # Tendências e Desafios
                             "digitalização", "indústria 4.0", "automação", "inteligência artificial", \
                             "machine learning", "iot", "sensores", "controle de processo", \
                             "otimização", "eficiência operacional", "manutenção preditiva", \
                             "realidade aumentada", "drones", "monitoramento remoto", \
                             
                             # Associações e Entidades
                             "ibá", "indústria brasileira de árvores", "bracelpa", "abtcp", \
                             "associação brasileira técnica de celulose e papel", \
                             "confederação nacional da indústria", "cni", "fiesp", \
                             "sindicato", "federação", "conselho setorial", \
                             
                             # Aspectos Internacionais
                             "china", "europa", "ásia", "estados unidos", "américa latina", \
                             "mercado internacional", "competitividade", "barreiras comerciais", \
                             "antidumping", "taxa de importação", "acordo comercial", \
                             "organização mundial do comércio", "omc"],        
        "Setor de Mineração": ["mineração", "mineradora", "minério", "ferro", "níquel", "ouro", "metal", "geologia", "jazida", "mina", "mining", \
                      
                      # Minerais e Metais
                      "cobre", "alumínio", "bauxita", "zinco", "chumbo", "estanho", "manganês", "cromo", "vanádio", \
                      "titânio", "molibdênio", "tungstênio", "cobalto", "lítio", "terras raras", "nióbio", \
                      "tântalo", "grafita", "quartzo", "feldspato", "caulim", "bentonita", "talco", \
                      "fosfato", "potássio", "sal", "calcário", "dolomita", "gipsita", "areia", "brita", \
                      "argila", "granito", "mármore", "ardósia", "quartzito", \
                      
                      # Empresas do Setor
                      "vale", "csr", "companhia siderúrgica nacional", "usiminas", "gerdau", "anglo american", \
                      "bhp", "rio tinto", "freeport mcmoran", "newmont", "barrick gold", "kinross", \
                      "yamana gold", "eldorado gold", "equinox gold", "jaguar mining", "mineração usiminas", \
                      "samarco", "braskem", "mosaic", "yara", "fertilizantes heringer", "galvani", \
                      "cmoc", "china molybdenum", "sigma lithium", "cbmm", "niobec", \
                      
                      # Processos de Mineração
                      "lavra", "beneficiamento", "concentração", "flotação", "lixiviação", "calcinação", \
                      "sinterização", "pelotização", "cominuição", "britagem", "moagem", "peneiramento", \
                      "classificação", "separação magnética", "separação gravimétrica", "espessamento", \
                      "filtragem", "secagem", "ustulação", "redução", "refinação", "fundição", \
                      "eletrólise", "hidrometalurgia", "pirometalurgia", "solvent extraction", \
                      
                      # Tipos de Mineração
                      "mina a céu aberto", "mina subterrânea", "cava", "tajo", "bancada", "talude", \
                      "galeria", "túnel", "poço", "pilha de estéril", "pilha de rejeito", \
                      "barragem de rejeitos", "dique", "dragagem", "garimpagem", "garimpo", \
                      "mineração artesanal", "pequena mineração", "grande mineração", \
                      
                      # Equipamentos e Tecnologia
                      "escavadeira", "carregadeira", "caminhão fora de estrada", "perfuratriz", \
                      "britador", "moinho", "ciclone", "espessador", "filtro prensa", \
                      "separador magnético", "mesa vibratória", "jigue", "espiral", \
                      "célula de flotação", "correias transportadoras", "guindastes", \
                      "dragline", "shovel", "wheel loader", "haul truck", \
                      
                      # Produtos e Commodities
                      "minério de ferro", "pellets", "sinter feed", "lump ore", "concentrado", \
                      "catodo", "anodo", "lingote", "barra", "chapa", "bobina", "vergalhão", \
                      "aço", "ferro gusa", "ferro esponja", "aço inoxidável", "liga metálica", \
                      "fertilizante", "rocha fosfática", "superfosfato", "map", "dap", \
                      
                      # Aspectos Ambientais
                      "licenciamento mineral", "estudo de impacto ambiental mineral", "recuperação de áreas", \
                      "plano de fechamento de mina", "pafem", "monitoramento ambiental", \
                      "gestão de rejeitos", "barragem de contenção", "estabilidade de taludes", \
                      "drenagem ácida", "contaminação do solo", "poluição hídrica", \
                      "poeira mineral", "ruído", "vibração", "subsídência", \
                      
                      # Regulamentação e Órgãos
                      "anm", "agência nacional de mineração", "dnpm", "código de mineração", \
                      "cfem", "compensação financeira", "royalties minerais", "taxa de fiscalização", \
                      "alvará de pesquisa", "concessão de lavra", "guia de utilização", \
                      "licenciamento", "ato autorizativo", "regime de extração", \
                      "permissão de lavra garimpeira", "plg", "registro de extração", \
                      
                      # Segurança e Saúde
                      "segurança do trabalho", "acidente de trabalho", "pneumoconiose", "silicose", \
                      "asbestose", "nr 22", "norma regulamentadora", "cipa", "sesmt", \
                      "equipamento de proteção individual", "epi", "ventilação", "iluminação", \
                      "explosivos", "blasting", "desmonte", "fogo", "detonação", \
                      
                      # Geologia e Pesquisa Mineral
                      "prospecção", "pesquisa mineral", "exploração geológica", "sondagem", \
                      "testemunho", "amostragem", "análise química", "ensaio", "teor", \
                      "reserva mineral", "recurso mineral", "cubagem", "avaliação de reservas", \
                      "modelo geológico", "corpo de minério", "veio", "camada", "lente", \
                      "alteração hidrotermal", "metamorfismo", "intemperismo", "oxidação", \
                      
                      # Aspectos Econômicos
                      "preço do minério", "cotação internacional", "bolsa de metais", "lme", \
                      "london metal exchange", "comex", "shfe", "contrato futuro", \
                      "hedge", "volatilidade", "supply chain", "cadeia produtiva", \
                      "custo de produção", "capex", "opex", "cash cost", "all in cost", \
                      "margem operacional", "ebitda", "viabilidade econômica", \
                      
                      # Logística e Transporte
                      "porto mineraleiro", "terminal portuário", "pátio de estocagem", \
                      "ferrovia", "mineroduto", "navio graneleiro", "carregamento", \
                      "descarga", "britador móvel", "usina de beneficiamento", \
                      "correia transportadora", "sistema de transporte", \
                      
                      # Sustentabilidade e ESG
                      "mineração sustentável", "economia circular", "reaproveitamento", \
                      "coprodutos", "subprodutos", "mineração urbana", "reciclagem de metais", \
                      "responsabilidade social", "relacionamento comunitário", \
                      "desenvolvimento local", "impacto socioeconômico", \
                      
                      # Mercados e Regiões
                      "quadrilátero ferrífero", "serra dos carajás", "província mineral", \
                      "distrito mineiro", "minas gerais", "pará", "mato grosso", "goiás", \
                      "bahia", "rondônia", "amazonas", "vale do jequitinhonha", \
                      "exportação mineral", "china", "japão", "coreia do sul", \
                      
                      # Tecnologia e Inovação
                      "mineração 4.0", \
                      "iot", "internet das coisas", "sensores", "drones", "veículos autônomos", \
                      "realidade aumentada", "simulação", "modelagem 3d", "geostatística", \
                      "analytics", "eficiência operacional", \
                      
                      # Aspectos Legais e Contratuais
                      "joint venture", "offtake agreement", \
                      "streaming", "royalty", "contrato de fornecimento", "take or pay", \
                      "arbitragem", "disputas comerciais", "compliance", \
                      
                      # Financiamento e Investimento
                      "project finance", "financiamento de projeto", "equity", "debt", \
                      "bndes", "banco de desenvolvimento", "agência de fomento", \
                      "investimento estrangeiro", \
                      "oferta pública"],        
        "Setor de Agronegócios": ["agronegócio", "agro", "pecuária", "lavoura", "safra", "colheita", "carne", "carnes", "laranja", \
                                "exportação agrícola", "rural", "agribusiness", "gripe aviária", "avícolas", "derivados", "frango", "ovos", \
                                "cacau", "crédito rural", "h5n1", "rastreabilidade", "tecnologia agrícola", "inovação agrícola", "caprinos", \
                                "ovinos", "abpa", "agricultura", "alimentos", "alimentação", "segurança alimentar", \
                                "subnutrição", "nutrição", "fao", \
                                
                                # Culturas e produtos agrícolas adicionais
                                "arroz", "feijão", "cana-de-açúcar", "algodão", "girassol", "canola", "amendoim", \
                                "mandioca", "batata", "tomate", "banana", "manga", "abacaxi", "uva", "maçã", "açaí", "guaraná", \
                                "eucalipto", "pinus", "seringueira", "dendê", "castanha", "quinoa", "chia", "aveia", \
                                "aves", "bezerro", "gado", "boi", "bovina", "suína", 
                                
                                # Pecuária e produtos animais
                                "bovinos", "suínos", "aves", "peixes", "aquicultura", "piscicultura", "leite", "queijo", "manteiga", \
                                "mel", "própolis", "geleia real", "couro", "lã", "búfalos", "equinos", "apicultura", \
                                "bovinocultura", "suinocultura", "avicultura", "ovinocultura", "caprinocultura", \
                                
                                # Tecnologia e inovação
                                "agricultura de precisão", "drones agrícolas", "sensoriamento remoto", "gps agrícola", "iot rural", \
                                "biotecnologia", "transgênicos", "ogm", "melhoramento genético", "sementes híbridas", \
                                "vertical farming", \
                                "hidroponia", "aeroponia", "agricultura urbana", "estufa", "irrigação automatizada", \
                                
                                # Sustentabilidade e meio ambiente
                                "agricultura sustentável", "orgânicos", "agroecologia", "certificação orgânica", "biológicos", \
                                "carbono neutro", "sequestro de carbono", "agricultura regenerativa", "plantio direto", \
                                "rotação de culturas", "sistema integrado", "ilpf", "reflorestamento", "desmatamento", \
                                "código florestal", "reserva legal", "app", "bioma", "cerrado", "amazônia", "mata atlântica", \
                                
                                # Economia e mercado
                                "preços agrícolas", "inflação alimentar", "pib agro", "logística agrícola", "armazenagem", "silo", \
                                
                                # Insumos e equipamentos
                                "fertilizantes", "defensivos", "agrotóxicos", "pesticidas", "herbicidas", "fungicidas", \
                                "inseticidas", "adubo", "calcário", "ureia", "fosfato", "potássio", "npk", \
                                "máquinas agrícolas", "tratores", "colheitadeiras", "plantadeiras", "pulverizadores", \
                                "implementos", \
                                
                                # Organizações e instituições
                                "embrapa", "incra", "ibge", "ministério da agricultura", "ministério da agricultura e pecuária (mapa)", "cna", "ocb", \
                                "faeg", "faesp", "faerj", "sindicatos rurais", "cooperativas", "agroindústria", \
                                "usinas", "frigoríficos", \
                                
                                # Políticas e programas
                                "pronaf", "pronamp", "plano safra", "pap", "pgpaf", "seguro rural", "proagro", \
                                "funrural", "itr", "car", "snir", "sicar", "incra", "reforma agrária", \
                                "agricultura familiar", "mst", "assentamentos", \
                                
                                # Clima e riscos
                                "seca", "estiagem", "geada", "granizo", "el niño", "la niña", \
                                "mudanças climáticas", "aquecimento global", "fenômenos climáticos", \
                                "zoneamento agrícola", "risco climático", "seguro agrícola", \
                                
                                # Pragas e doenças
                                "pragas", "fungos", "antracnose", "fusarium", \
                                "manejo integrado", "controle biológico", \
                                
                                # Qualidade e certificação
                                "bpa", "bpf", "haccp", "globalg.a.p", \
                                "fair trade", "rainforest alliance", "utz", "4c", "rtrs", "proterra", \
                                                                
                                # Processamento e indústria
                                "agroindústria", "food tech", "alimentos funcionais", "suplementos", \
                                "proteína vegetal", "carne vegetal", "plant based", "lab grown meat"],
        "Setor de Educação": ["educação", "escola", "universidade", "ensino", "aluno", "professor", "faculdade", "curso", "vestibular", \
                            "enem", "educacional", "estudante", "estudantes", "vestibulares", "educacional", "educacionais", "docente", \
                            "aprendizagem", "ead", "mec", \
                            # Programas de financiamento e bolsas
                            "fies", "fundo de financiamento estudantil", "prouni", "programa universidade para todos", \
                            "bolsa de estudos", "financiamento estudantil", "crédito educativo", "bolsa integral", "bolsa parcial", \
                            "auxílio estudantil", "auxílio permanência", "pnaes", "programa nacional de assistência estudantil", \
                            
                            # Aspectos financeiros do FIES
                            "dívida estudantil", \
                            "contrato fies", \
                            "ministério da educação", \
                            
                            # Órgãos e instituições governamentais
                            "ministério da educação", "inep", "capes", "cnpq", "fnde", "fundo nacional de desenvolvimento da educação", \
                            "consed", "undime", "conae", "conselho nacional de educação", "cne", "conaes", \
                            "instituto nacional de estudos e pesquisas educacionais", "fundação capes", \
                            
                            # Níveis de ensino
                            "educação infantil", "ensino fundamental", "ensino médio", "ensino superior", "pós-graduação", \
                            "mestrado", "doutorado", "pós-doutorado", "educação básica", "educação profissional", \
                            "ensino técnico", "formação profissional", "qualificação profissional", \
                            
                            # Modalidades de ensino
                            "educação a distância", "ensino presencial", "ensino híbrido", "ensino remoto", \
                            "educação online", "aulas virtuais", "plataforma digital", "ambiente virtual de aprendizagem", \
                            "ava", "mooc", "educação semipresencial", \

                            # Avaliações e indicadores
                            "ideb", "índice de desenvolvimento da educação básica", "saeb", "prova brasil", \
                            "ana", "avaliação nacional de alfabetização", "pisa", "enade", "cpc", "conceito preliminar de curso", \
                            "igd", "sinaes", "sistema nacional de avaliação da educação superior", \
                            
                            # Currículos e diretrizes
                            "bncc", "base nacional comum curricular", "dcn", "diretrizes curriculares nacionais", \
                            "pcn", "parâmetros curriculares nacionais", "projeto pedagógico", "ppp", \
                            "matriz curricular", "grade curricular", "ementa", "plano de ensino", \
                            
                            # Formação de professores
                            "formação docente", "licenciatura", "pedagogia", "magistério", "formação continuada", \
                            "capacitação docente", "pibid", "residência pedagógica", \
                            "programa institucional de bolsas de iniciação à docência", \
                            
                            # Instituições de ensino superior
                            "ies", "instituição de ensino superior", "universidade federal", "universidade estadual", \
                            "universidade particular", "universidade privada", "centro universitário", "faculdade isolada", \
                            "instituto federal", "ifes", "cefet", "universidade comunitária", \
                            
                            # Gestão educacional
                            "gestão escolar", "coordenador pedagógico", "supervisor escolar", \
                            "secretaria de educação", "conselho escolar", "grêmio estudantil", "apm", \
                            "associação de pais e mestres", "projeto político pedagógico", \
                            
                            # Inclusão e diversidade
                            "educação inclusiva", "educação especial", "aee", "atendimento educacional especializado", \
                            "libras", "braile", "deficiência", "necessidades especiais", "educação indígena", \
                            "educação quilombola", "educação do campo", "eja", "educação de jovens e adultos", \
                            
                            # Tecnologia educacional
                            "tecnologia educacional", "informática educativa", "robótica educacional", \
                            "laboratório de informática", "lousa digital", "tablet educacional", \
                            "computador por aluno", "internet nas escolas", "banda larga nas escolas", \
                            
                            # Estrutura física e recursos
                            "infraestrutura escolar", "biblioteca", "refeitório", "transporte escolar", "merenda escolar", "pnae", \
                            "programa nacional de alimentação escolar", "livro didático", "pnld", \
                            
                            # Alfabetização e letramento
                            "alfabetização", "letramento", "analfabetismo", "analfabetismo funcional", \
                            "pnaic", "pacto nacional pela alfabetização na idade certa", "método fônico", \
                            "método global", "psicogênese da língua escrita", \
                            
                            # Ensino profissional e técnico
                            "senai", "senac", "sistema s", "aprendizagem industrial", "jovem aprendiz", \
                            "pronatec", "programa nacional de acesso ao ensino técnico e emprego", \
                            "fic", "formação inicial e continuada", "itinerário formativo", \
                            
                            # Políticas educacionais
                            "pne", "plano nacional de educação", "fundeb", "fundef", "piso salarial", \
                            "carreira docente", "valorização do magistério", "meta do pne", \
                            "regime de colaboração", "pacto federativo", "municipalização", \
                            
                            # Pesquisa e inovação
                            "pesquisa científica", "iniciação científica", "pibic", "inovação educacional", \
                            "extensão universitária", "tripé universitário", "ensino pesquisa extensão", \
                            "produção científica", "publicação acadêmica", "revista científica", \
                            
                            # Internacionalização
                            "intercâmbio", "mobilidade acadêmica", "ciência sem fronteiras", "capes print", \
                            "dupla titulação", "acordo de cooperação", "universidade estrangeira", \
                            "reconhecimento de diploma", "revalidação de diploma", \
                            
                            # Vestibulares e processos seletivos
                            "sisu", "sistema de seleção unificada", "prosel", "processo seletivo", \
                            "nota de corte", "lista de espera", "chamada regular", "chamada complementar", \
                            "fuvest", "comvest", "vunesp", "cesgranrio", "acafe", \
                            
                            # Regulamentação e credenciamento
                            "autorização de curso", "reconhecimento de curso", "renovação de reconhecimento", \
                            "credenciamento", "recredenciamento", "supervisão", "regulação", \
                            "conceito de curso", "nota do enade", "cpc", "ci", "conceito institucional", \
                            
                            # Evasão e permanência
                            "evasão escolar", "abandono escolar", "repetência", "distorção idade-série", \
                            "taxa de aprovação", "taxa de reprovação", "fluxo escolar", \
                            "diplomação", "tempo médio de formação", \
                            
                            # Educação corporativa e continuada
                            "educação corporativa", "treinamento", "capacitação", "desenvolvimento profissional", \
                            "educação executiva", "mba", "master business administration", \
                            "educação continuada", "atualização profissional", "reciclagem", \
                            
                            # Sindicatos e entidades
                            "cnte", "andes", "fasubra", "andifes", "abruem", "abmes", \
                            "sindicato dos professores", "federação dos professores", "entidade estudantil", \
                            "une", "ubes", "diretório acadêmico", "centro acadêmico"],
        "Setor de Energia": ["energia", "elétrica", "usina", "hidrelétrica", "termelétrica", "eólica", "solar", "transmissão", "distribuição", \
                            "gasolina", "diesel", "etanol", "combustível", "petróleo", "gás", "conta de luz", "mme",
                            # Energia Solar e Fotovoltaica
                            "fotovoltaica", "fotovoltaico", "painéis solares", "células solares", "silício", "módulos solares", \
                            "irradiação solar", "radiação solar", "heliotérmica", "energia heliotérmica", \
                            "inversores", "rastreamento solar", "tracker", "string", "mppt", \
                            "parque solar", "fazenda solar", "complexo solar", "usina fotovoltaica", \
                            
                            # Energia Eólica
                            "parque eólico", "fazenda eólica", "aerogerador", "turbina eólica", "torre eólica", \
                            "ventos", "velocidade do vento", "offshore", "onshore eólica", \
                            "nacele", "rotor", "pás", "gerador eólico", \
                            
                            # Capacidade e Medidas Técnicas
                            "mw", "megawatt", "megawatts", "gw", "gigawatt", "gigawatts", "kw", "quilowatt", \
                            "mwh", "megawatt-hora", "gwh", "gigawatt-hora", "kwh", "quilowatt-hora", \
                            "mwac", "mwdc", "corrente alternada", "corrente contínua", \
                            "capacidade instalada", "fator de capacidade", "potência instalada", \
                            "geração de energia", "produção energética", \
                            
                            # Infraestrutura Elétrica
                            "subestação", "linha de transmissão", "rede elétrica", "sistema interligado nacional", "sin", \
                            "kv", "quilovolt", "quilovolts", "alta tensão", "média tensão", "baixa tensão", \
                            "transformador", "disjuntor", "seccionador", "religador", \
                            "ons", "operador nacional do sistema", "câmara de comercialização", \
                            
                            # Mercado de Energia
                            "acl", "ambiente de contratação livre", "ace", "ambiente de contratação regulada", \
                            "leilão de energia", "ppa", "contrato de compra de energia", \
                            "comercialização de energia", "trader de energia", "ccee", \
                            "preço da energia", "pld", "preço de liquidação das diferenças", \
                            "bandeira tarifária", "bandeira vermelha", "bandeira amarela", "bandeira verde", \
                            
                            # Financiamento e Desenvolvimento
                            "bndes", "finem", "fundo clima", "financiamento de projetos", \
                            "investimento em energia", "capex", "opex", \
                            "epc", "engineering procurement construction", \
                            "o&m", "operação e manutenção", \
                            
                            # Sustentabilidade e Meio Ambiente
                            "energia renovável", "energia limpa", "energia sustentável", \
                            "descarbonização", "transição energética", "matriz energética", \
                            "emissões de co2", "pegada de carbono", "neutralidade carbônica", \
                            "agenda verde", "emergência climática", "mudanças climáticas", \
                            "rca", "certificado de energia renovável", \
                            
                            # Empresas e Players do Setor
                            "atlas renewable energy", "enel", "cpfl", "energisa", "equatorial", \
                            "light", "cemig", "copel", "eletrobras", "furnas", "chesf", \
                            "geradora", "distribuidora", "transmissora", "comercializadora", \
                            "startup de energia", "fintech de energia", "proptech energia", \
                            
                            # Tecnologias Emergentes
                            "armazenamento de energia", "baterias", "hidrogênio verde", "hidrogênio", \
                            "smart grid", "rede inteligente", "medidor inteligente", "iot energia", \
                            "energia das ondas", "energia maremotriz", "biomassa", "biogás", \
                            "cogeração", "trigeração", "microgeração", "minigeração", \
                            "geração distribuída", "prosumidor", "autoconsumo", \
                            
                            # Regulamentação e Órgãos
                            "aneel", "agência nacional de energia elétrica", \
                            "epe", "empresa de pesquisa energética", \
                            "regulamentação energética", "resolução aneel", "consulta pública", \
                            "tarifa de energia", "reajuste tarifário", "revisão tarifária", \
                            
                            # Tipos de Usinas e Tecnologias
                            "pch", "pequena central hidrelétrica", "cgh", "central geradora hidrelétrica", \
                            "uhe", "usina hidrelétrica", "ute", "usina termelétrica", \
                            "nuclear", "usina nuclear", "angra", "reator nuclear", \
                            "carvão", "gás natural", "óleo combustível", "bagaço de cana", \
                            
                            # Eficiência Energética
                            "eficiência energética", "conservação de energia", "consumo energético", \
                            "auditoria energética", "selo procel", "etiquetagem energética", \
                            "led", "iluminação eficiente", "aquecimento solar", \
                            "ciclo combinado", \
                            
                            # Aspectos Econômicos
                            "tarifa energética", "conta de energia", "fatura de energia", \
                            "subsídio energético", "cde", "conta de desenvolvimento energético", \
                            "encargo energético", "pis/cofins energia", "icms energia", \
                            "mercado livre de energia", "migração para mercado livre", \
                            
                            # Dados Centers e Consumo Industrial
                            "consumo industrial", \
                            "grande consumidor", "eletrointensivo", \
                            "demanda energética", "curva de carga", "fora de ponta", \
                            
                            # Projetos e Desenvolvimento
                            "projeto energético", "desenvolvimento de projetos", "greenfield", "brownfield", \
                            "due diligence energética", "viabilidade energética", "estudo de viabilidade", \
                            "licenciamento energético", "eia-rima energia", \
                            "conexão ao sistema", "acesso ao sistema", "parecer de acesso", \
                            
                            # Empregos e Impacto Social
                            "empregos na energia", "mão de obra energética", "capacitação energética", \
                            "impacto social", "comunidades locais", "reassentamento", \
                            "desenvolvimento regional", "royalties", "compensação energética"],                        
        "Setor de Finanças": ["finanças", "banco", "crédito", "investimento", "investimentos", "mercado financeiro", "mercados", "ação", "renda fixa", \
                            "câmbio", "dívida", "lucro", "capital", "IPO", "banco central", "política monetária", "política econômica", "governo", \
                            "ações", "fundos", "balanço", "balanços", "bolsa", "nasdaq", "etf", "tributação", "contribuinte", "selic", "juros", \
                            "precatórios", "inflação", "deficit fiscal", "ibs", "cbs", "ibovespa", "b3", "iof", \
                            # Bancos e instituições financeiras
                            "banco do brasil", "caixa econômica federal", "bndes", "bradesco", "itaú", "santander", \
                            "banco inter", "nubank", "c6 bank", "original", "safra", "votorantim", "btg pactual", \
                            "xp investimentos", "rico", "clear", "easynvest", "avenue", "toro investimentos", \
                            "warren", "modalmais", "órama", "genial investimentos", "mirae asset", "guide investimentos", \
                            
                            # Mercado de capitais
                            "bovespa", "cetip", "selic", "cdi", "copom", "comitê de política monetária", \
                            "mercado de balcão", "mercado de balcão organizado", "novo mercado", "nível 1", "nível 2", \
                            "governança corporativa", "listagem", "abertura de capital", "oferta pública inicial", \
                            "follow on", "oferta subsequente", "bookbuilding", "roadshow", "prospecto", \
                            
                            # Instrumentos financeiros
                            "debêntures", "cra", "cri", "lci", "lca", "cdb", "rdb", "letra de câmbio", \
                            "dpge", "tesouro direto", "tesouro selic", "tesouro prefixado", "tesouro ipca", \
                            "ntn-b", "lft", "ltn", "ntn-f", "swap", "derivativos", "opções", "futuro", \
                            "commodity", \
                            
                            # Fundos de investimento
                            "fundo de investimento", "fundo de ações", "fundo multimercado", "fundo imobiliário", \
                            "fii", "fundo de renda fixa", "fundo cambial", "fundo de commodities", \
                            "fundo quantitativo", "fundo long short", "fundo macro", "fundo estruturado", \
                            "gestora", "administradora", "custodiante", "taxa de administração", \
                            "taxa de performance", "come-cotas", "cotização", "resgate", "aplicação", \

                            # Indicadores econômicos
                            "pib", "produto interno bruto", "ipca", "inpc", "igp-m", "igp-di", "ipa", "incc", \
                            "ipc", "ipc-fipe", "taxa selic", "taxa di", "focus", "boletim focus", \
                            "expectativas", "projeções", "meta de inflação", "banda de inflação", \
                            "crescimento econômico", "recessão", "depressão", "estagnação", "recuperação", \
                            
                            # Política fiscal
                            "orçamento público", "lei orçamentária anual", "loa", "ldo", "ppa", \
                            "receita federal", "arrecadação", "tributos", "impostos", "contribuições", \
                            "ir", "imposto de renda", "pis", "cofins", "csll", "ipi", "icms", "iss", \
                            "simples nacional", "lucro presumido", "lucro real", "refis", "pert", \
                            "parcelamento", "anistia", "remissão", "moratória", \
                            
                            # Comércio exterior e câmbio
                            "exportação", "importação", "balança comercial", "saldo comercial", "superávit", \
                            "déficit", "balança de pagamentos", "conta corrente", "conta capital", \
                            "reservas internacionais", "bacen", "ptax", "taxa de câmbio", "dólar", \
                            "euro", "iene", "libra", "peso argentino", "real", "moeda", "divisa", \
                            "hedge cambial", "swap cambial", "derivatives", "ndf", \
                            
                            # Tarifas e comércio internacional
                            "tarifa", "tarifaço", "sobretaxa", "alíquota", "quota", "contingente", \
                            "anti-dumping", "salvaguarda", "medida compensatória", "omc", "organização mundial do comércio", \
                            "acordo comercial", "tratado comercial", "zona de livre comércio", "união aduaneira", \
                            "mercosul", "alca", "nafta", "usmca", "cptpp", "rcep", \
                            "câmara de comércio", "amcham", "federação das indústrias", "cnc", "cni", \
                            
                            # Empresas e setores econômicos
                            "venture capital", \
                            "private equity", "m&a", "fusões e aquisições", "joint venture", \
                            
                            # Regulamentação financeira
                            "cvm", "comissão de valores mobiliários", "susep", "previc", "coaf", \
                            "febraban", "anbima", "abecip", "anefac", "apimec", "ibcpf", \
                            "resolução", "instrução", "circular", "comunicado", "carta-circular", \
                            "basiléia", "acordo de basiléia", "capital regulatório", "tier 1", "tier 2", \
                            
                            # Rating e análise de crédito
                            "rating", "classificação de risco", "grau de investimento", "grau especulativo", \
                            "moody's", "standard & poor's", "fitch", "serasa", "spc", "scr", \
                            "cadastro positivo", "bureau de crédito", "score", "inadimplência", \
                            "default", "calote", "renegociação", "feirão de negociação", \
                            
                            # Previdência e seguros
                            "previdência social", "inss", "rgps", "rpps", "previdência complementar", \
                            "previdência privada", "pgbl", "vgbl", "eapc", "efpc", "seguro de vida", \
                            "seguro auto", "seguro residencial", "seguro empresarial", "resseguro", \
                            "cosseguro", "franquia", "sinistro", "indenização", "prêmio", \
                            
                            # Fintechs e tecnologia financeira
                            "fintech", "insurtech", "proptech", "regtech", "suptech", "blockchain", \
                            "bitcoin", "criptomoeda", "moeda digital", "pix", "ted", "doc", \
                            "open banking", "sandbox regulatório", \
                            "inteligência artificial", "big data", "analytics", "robo advisor", \
                            
                            # Mercado imobiliário
                            "mercado imobiliário", "financiamento imobiliário", "sistema financeiro da habitação", \
                            "sfh", "sbpe", "fgts", "caixa econômica", "minha casa minha vida", \
                            "mcmv", "construtora", "incorporadora", "loteamento", "condomínio", \
                            "cartório de registro de imóveis", "itbi", "iptu", \
                            
                            # Economia internacional
                            "fed", "federal reserve", "bce", "banco central europeu", "boj", \
                            "banco do japão", "pboc", "banco popular da china", "fmi", \
                            "fundo monetário internacional", "banco mundial", "bid", \
                            "banco interamericano de desenvolvimento", "g7", "g20", "brics", \
                            "ocde", "davos", "fórum econômico mundial", \
                            
                            # Análise técnica e fundamentalista
                            "análise técnica", "análise fundamentalista", "candlestick", \
                            "média móvel", \
                            "rsi", "macd", "bollinger", "fibonacci", "pivot", "day trade", \
                            "swing trade", "buy and hold", "valuation", "múltiplos", \
                            
                            # Gestão de riscos
                            "risco de mercado", "risco de crédito", "risco operacional", "risco de liquidez", \
                            "risco país", "embi+", "cds", "value at risk", "var", "stress test", \
                            "backtesting", "compliance", "governança", "auditoria", "controladoria", \
                            
                            # Micro e macroeconomia
                            "microeconomia", "macroeconomia", "oferta", "demanda", "elasticidade", \
                            "utilidade", "externalidade", "monopólio", "oligopólio", \
                            "concorrência perfeita", "teoria dos jogos", "assimetria de informação", \
                            "ciclos econômicos", "multiplicador", "acelerador", "curva de phillips", \
                            
                            # Startups e empreendedorismo
                            "angel investor", "seed", "series a", "series b", "ipo", "spac", \
                            "bootstrapping", "burn rate", "runway", "pivot", "mvp", \
                            "produto mínimo viável", "tração", "churn", "ltv", "cac", \
                            ],
        "Setor de Óleo de Gás": ["óleo", "gás", "petróleo", "exploração", "refinaria", "gasoduto", "poço", "onshore", "offshore", \
                                "glp", "petrobras", "anp", \
                                # Empresas e instituições do setor
                                "shell", "chevron", "exxon", "bp", "total", "equinor", "repsol", "eni", "3r petroleum", \
                                "prio", "enauta", "karoon", "murphy oil", "galp", "vibra energia", "raízen", "ipiranga", \
                                "ultrapar", "br distribuidora", "ale combustíveis", \
                                
                                # Órgãos reguladores e governamentais
                                "mme", "ministério de minas e energia", "cade", "ibama", "cnpe", "ppsa", "pré-sal petro", \
                                "agência nacional do petróleo", "licenciamento ambiental", "licença ambiental", \
                                
                                # Tipos de petróleo e derivados
                                "brent", "wti", "crude", "petróleo bruto", "diesel", "gasolina", "querosene", "nafta", \
                                "óleo combustível", "bunker", "asfalto", "parafina", "querosene de aviação", "jet fuel", \
                                "gasóleo", "coque", "enxofre", "gnl", "gás natural liquefeito", "gnc", "gás natural comprimido", \
                                
                                # Infraestrutura e equipamentos
                                "sonda", "plataforma", "fpso", "refinaria", "terminal", "oleoduto", "gasoduto", "pipeline", \
                                "usina de processamento", "compressor", "válvula", "bomba", "tanque", "tancagem", \
                                "porto", "pier", "navio petroleiro", "navio gaseiro", \
                                
                                # Processos e tecnologia
                                "perfuração", "completação", "produção", "estimulação", "fraturamento", "acidificação", \
                                "workover", "cimentação", "perfilagem", "sísmica", "geofísica", "geologia", \
                                "reservatório", "jazida", "campo", "bloco exploratório", "concessão", \
                                "partilha de produção", "cessão onerosa", \
                                
                                # Operações upstream
                                "exploração e produção", "e&p", "upstream", \
                                "reservas", "barril", "bpd", "barris por dia", \
                                "fator de recuperação", "ior", "eor", "recuperação avançada", \
                                
                                # Operações midstream e downstream
                                "midstream", "downstream", "refino", "craqueamento", "destilação", \
                                "hidrotratamento", "reforma catalítica", "alquilação", "coqueamento", \
                                "petroquímica", "química", "fertilizantes", \
                                
                                # Distribuição e varejo
                                "posto", "abastecimento", "combustível", "etanol", \
                                "biodiesel", "aditivo", "lubrificante", "bandeira branca", "tr", \
                                
                                # Bacias sedimentares brasileiras
                                "bacia de campos", "bacia de santos", "bacia do espírito santo", "bacia de sergipe-alagoas", \
                                "bacia do recôncavo", "bacia potiguar", "bacia do ceará", "bacia de barreirinhas", \
                                "bacia da foz do amazonas", "margem equatorial", "pré-sal", "pós-sal", \
                                "águas profundas", "águas ultraprofundas", \

                                # Aspectos ambientais e sustentabilidade
                                "vazamento", "derramamento", "oil spill", "impacto ambiental", "eia-rima", \
                                "compensação ambiental", "remediação", "captura de carbono", \
                                "ccus", "descarbonização", "transição energética", \
                                
                                # Regulamentação e contratos
                                "bid round", "contrato de concessão", \
                                "contrato de partilha", "marco regulatório", "lei do petróleo", "ans", \
                                "área de acumulação marginal", "campo maduro", \
                                
                                # Mercado e economia
                                "preço do petróleo", "margem de refino", \
                                "opep", "opep+", \
                                "aie", "agência internacional de energia", "estoques estratégicos", \
                                
                                # Segurança e operações
                                "segurança operacional", "hse", "blowout", "kick", "controle de poço", \
                                "bop", "salvatagem", \
                                
                                # Transporte marítimo
                                "afretamento", "charter", "vlcc", "suezmax", "aframax", "panamax", \
                                "handysize", "lng carrier", "shuttle tanker", "fso", "flng", \
                                
                                # Aspectos internacionais
                                "bacia de neuquén", "vaca muerta", "permian basin", "eagle ford", \
                                "mar do norte", "golfo do méxico"], \
        "Justiça": ["justiça", "judiciário", "tribunal", "juiz", "ministério público", "processo", "sentença", "condenação", "advogado", \
                    "lei", "legal", "stf", "supremo", "pena", "penas", "jurisprudência", "pgr", "julgamento", "recurso", "judicial", \
                    "denúncia", "acusação", "stj", "cnj", "golpe de estado", "penduricalhos", "agu", "alexandre de moraes", \
                    # Tribunais superiores e especializados
                    "supremo tribunal federal", "superior tribunal de justiça", "tribunal superior eleitoral", "tse", \
                    "tribunal superior do trabalho", "tst", "superior tribunal militar", "stm", \
                    "tribunal de justiça", "tj", "tribunal regional federal", "trf", "tribunal regional eleitoral", "tre", \
                    "tribunal regional do trabalho", "trt", "tribunal de contas", "tcu", "tce",  \
                    "tribunal do júri", "vara criminal", "vara cível", "vara federal", "vara eleitoral", \
                    "vara do trabalho", "vara de família", "juizado especial", "juizado cível", "juizado criminal", \
                    
                    # Ministério Público
                    "procurador-geral da república", "procurador da república", "promotor de justiça", \
                    "ministério público federal", "mpf", "ministério público estadual", "mpe", \
                    "ministério público do trabalho", "mpt", "ministério público militar", "mpm", \
                    "procuradoria", "promotoria", "força-tarefa", "investigação", \
                    
                    # Operações e casos famosos
                    "lava jato", "operação lava jato", "car wash", "operação car wash", "deltan dallagnol", \
                    "sergio moro", "mensalão", "petrolão", "operação zelotes", "operação greenfield", \
                    "operação weak flesh", "operação carne fraca", "operação ghost writer", \
                    
                    # Processos e procedimentos
                    "ação penal", "ação civil", "habeas corpus", "mandado de segurança", "mandado de injunção", \
                    "ação direta de inconstitucionalidade", "adi", "arguição de descumprimento", "adpf", \
                    "ação declaratória de constitucionalidade", "adc", "agravo", "apelação", \
                    "embargos", "recurso especial", "recurso extraordinário", "repercussão geral", \
                    
                    # Decisões judiciais
                    "liminar", "tutela antecipada", "tutela de urgência", "medida cautelar", "decisão monocrática", \
                    "acórdão", "despacho", "alvará", "mandado", "intimação", "citação", "notificação", \
                    "sentença condenatória", "sentença absolutória", "absolvição", "arquivamento", \
                    
                    # Penas e medidas
                    "prisão", "detenção", "reclusão", "prisão temporária", "prisão preventiva", "prisão domiciliar", \
                    "liberdade condicional", "livramento condicional", "sursis", "regime fechado", "regime semiaberto", \
                    "regime aberto", "progressão de regime", "remição", "indulto", "graça", "anistia", \
                    "medida socioeducativa", "prestação de serviços", "multa", "reparação de danos", \

                    # Crimes e infrações
                    "crime", "delito", "contravenção", "infração", "homicídio", "roubo", "furto", "estelionato", \
                    "corrupção", "peculato", "concussão", "prevaricação", "improbidade administrativa", \
                    "lavagem de dinheiro", "evasão de divisas", "sonegação", "tráfico", "formação de quadrilha", \
                    "organização criminosa", "associação criminosa", "crime contra a ordem tributária", \
                    
                    # Direito civil e comercial
                    "indenização", "danos morais", "danos materiais", "responsabilidade civil", \
                    "inadimplência", "falência", "recuperação judicial", "concordata", \
                    "usucapião", "desapropriação", "divórcio", "guarda", \
                    
                    # Profissionais do direito
                    "magistrado", "desembargador", "ministro do supremo", "ministro do stj", "juiz federal", \
                    "juiz estadual", "juiz do trabalho", "juiz eleitoral", "defensor público", "procurador", \
                    "promotor", "advogado", "causa própria", "assistente de acusação", "curador", \
                    
                    # Órgãos auxiliares
                    "defensoria pública", "advocacia-geral da união", "procuradoria-geral", "ordem dos advogados", \
                    "oab", "conselho nacional de justiça", "escola da magistratura", "escola superior do mp", \
                    "corregedoria", "ouvidoria", "conselho nacional do mp", "cnmp", \
                    
                    # Procedimentos investigativos
                    "inquérito policial", "investigação criminal", "busca e apreensão", "interceptação telefônica", \
                    "quebra de sigilo", "colaboração premiada", "delação premiada", "acordo de leniência", \
                    "termo de ajustamento de conduta", "tac", "transação penal", "suspensão condicional", \
                    
                    # Direitos fundamentais
                    "habeas corpus", "habeas data", "mandado de segurança", "mandado de injunção", \
                    "ação popular", "direitos humanos", "devido processo legal", "ampla defesa", "contraditório", \
                    "presunção de inocência", "non bis in idem", "nulla poena sine lege", \
                    
                    # Direito eleitoral
                    "crime eleitoral", "abuso de poder", "compra de votos", "caixa dois", "propaganda irregular", \
                    "cassação de mandato", "inelegibilidade", "ficha limpa", "prestação de contas", \
                    "doação irregular", "captação irregular de recursos", \
                    
                    # Direito administrativo
                    "improbidade administrativa", "licitação", "pregão", "concurso público", "servidor público", \
                    "estatutário", "celetista", "nepotismo", "moralidade administrativa", \
                    "legalidade", "supremacia do interesse público", \
                    
                    # Processo penal
                    "flagrante", "auto de prisão", "boletim de ocorrência", "termo circunstanciado", \
                    "audiência de custódia", "interrogatório", "oitiva", "acareação", \
                    "perícia", "exame de corpo de delito", "laudo", "prova pericial", "testemunha", \
                    
                    # Execução penal
                    "execução da pena", "vara de execuções", "vep", "sistema penitenciário", "penitenciária", \
                    "presídio", "casa de detenção", "centro de ressocialização", "trabalho do preso", \
                    "estudo do preso", "visita íntima", "saída temporária", "monitoramento eletrônico", \
                    
                    # Medidas protetivas
                    "medida protetiva", "violência doméstica", "lei maria da penha", "feminicídio", \
                    "stalking", "assédio", "proteção à vítima", "programa de proteção", "casa abrigo", \
                    
                    # Direito da criança e adolescente
                    "estatuto da criança e do adolescente", "eca", "conselho tutelar", "vara da infância", \
                    "medida socioeducativa", "semiliberdade", "liberdade assistida", \
                    "prestação de serviços à comunidade", "advertência", "reparação do dano", \
                    
                    # Direito do consumidor
                    "código de defesa do consumidor", "cdc", "relação de consumo", \
                    "propaganda enganosa", "práticas abusivas", "procon", "superendividamento",
                    
                    # Direito ambiental
                    "crime ambiental", "dano ambiental", "licenciamento ambiental", "estudo de impacto", \
                    "termo de ajustamento de conduta ambiental", "compensação ambiental", "multa ambiental", \
                    
                    # Recursos e instâncias
                    "primeira instância", "segunda instância", "instância superior", "instância especial", \
                    "instância extraordinária", "duplo grau de jurisdição", "efeito suspensivo", "efeito devolutivo", \
                    "mérito", "preliminar", "nulidade", "anulação", \
                    
                    # Prazos processuais
                    "decadência", "prescrição", "caducidade", "preclusão", "perempção", \
                    "revelia", "contumácia", "impedimento", "suspeição", "incompetência", \
                    
                    # Valores e custas
                    "custas processuais", "taxa judiciária", "honorários advocatícios", "honorários sucumbenciais", \
                    "assistência judiciária gratuita", "justiça gratuita", "benefício da gratuidade", \
                    "depósito recursal", "porte de remessa", "diligências", "citação por edital"
                    ],
        "Meio Ambiente e ESG": ["meio ambiente", "sustentabilidade", "ambiental", "ambientalistas", "ecologia", "desmatamento", \
                                "poluição", "clima", "ESG", "governança ambiental", "responsabilidade social", "emissão de carbono", \
                                "biodiversidade", "amazônia", "floresta", "exploração", "cerrado", "mata atlântica", "cop30", \
                                "licenciamento ambiental", "créditos de carbono", "ibama",
                                # Licenciamento Ambiental e Regulamentação
                                "licença ambiental", "autorização ambiental", "nova lei do licenciamento", "lei geral do licenciamento", \
                                "lgla", "autodeclaração", "eia", "rima", "estudo de impacto ambiental", \
                                "relatório de impacto ambiental", "audiência pública", "compensação ambiental", \
                                "condicionantes ambientais", "renovação de licença", "licença prévia", "licença de instalação", \
                                "licença de operação", "lp", "li", "lo", "licença simplificada", "las", \
                                "licença por adesão e compromisso", "lac", "baixíssimo impacto", "impacto ambiental", \
                                
                                # Órgãos Ambientais e Instituições
                                "ministério do meio ambiente", "mma", "instituto chico mendes", "icmbio", \
                                "instituto nacional de pesquisas espaciais", "inpe", "agência nacional de águas", "ana", \
                                "conselho nacional do meio ambiente", "conama", "sistema nacional do meio ambiente", "sisnama", \
                                "órgão ambiental", "órgão licenciador", "secretaria de meio ambiente", \
                                "marina silva", "ministra do meio ambiente", \
                                
                                # Biomas e Ecossistemas
                                "pantanal", "caatinga", "pampa", "mangue", "restinga", "campos rupestres", \
                                "zona costeira", "unidades de conservação", "parque nacional", "reserva biológica", \
                                "estação ecológica", "área de proteção ambiental", "apa", "floresta nacional", \
                                "reserva extrativista", "resex", "reserva de desenvolvimento sustentável", "rds", \
                                
                                # Mudanças Climáticas e Carbono
                                "mudanças climáticas", "aquecimento global", "gases de efeito estufa", "gee", \
                                "protocolo de kyoto", "acordo de paris", "ndc", "contribuição nacionalmente determinada", \
                                "mercado de carbono", "compensação de carbono", "pegada de carbono", \
                                "inventário de emissões", "neutralidade de carbono", "carbono neutro", "net zero", \
                                "captura de carbono", "sequestro de carbono", "redd+", "floresta plantada", \
                                
                                # ESG e Sustentabilidade Corporativa
                                "ambiental social governança", "relatório de sustentabilidade", "relatório esg", \
                                "índice de sustentabilidade", "ise", "pacto global", "objetivos de desenvolvimento sustentável", \
                                "ods", "agenda 2030", "economia circular", "produção mais limpa", "tecnologia limpa", \
                                "inovação sustentável", "investimento sustentável", "finanças verdes", "green bonds", \
                                "taxonomia verde", "due diligence ambiental", \
                                
                                # Recursos Naturais e Conservação
                                "recursos hídricos", "gestão de águas", "bacia hidrográfica", "outorga de água", \
                                "comitê de bacia", "cobrança pelo uso da água", "sistema nacional de gerenciamento", \
                                "sngrh", "crise hídrica", "escassez hídrica", "uso múltiplo da água", \
                                "fauna", "flora", "espécies ameaçadas", "extinção", "conservação da biodiversidade", \
                                "corredor ecológico", "conectividade", "fragmentação", "habitat", \
                                
                                # Controle de Poluição
                                "controle de poluição", "monitoramento ambiental", "qualidade do ar", "qualidade da água", \
                                "poluição atmosférica", "poluição hídrica", "poluição do solo", "contaminação", \
                                "passivo ambiental", "remediação", "recuperação de áreas degradadas", "prad", \
                                "gerenciamento de resíduos", "resíduos sólidos", "aterro sanitário", "compostagem", \
                                "reciclagem", "logística reversa", "economia circular", \
                                
                                # Desenvolvimento Sustentável
                                "desenvolvimento sustentável", "sustentabilidade ambiental", "uso sustentável", \
                                "manejo sustentável", "certificação ambiental", "selo verde", "rotulagem ambiental", \
                                "produção sustentável", "consumo sustentável", "pegada ecológica", \
                                "capacidade de suporte", "limite planetário", "resilência ambiental", \
                                
                                # Fiscalização e Multas
                                "fiscalização ambiental", "multa ambiental", "infração ambiental", "auto de infração", \
                                "embargo", "apreensão", "termo de compromisso", "tac", "termo de ajustamento de conduta", \
                                "recuperação de danos", "reparação ambiental", "responsabilização ambiental", \
                                
                                # Energia Renovável e Limpa
                                "energia limpa", "energia renovável", "matriz energética sustentável", \
                                "transição energética", "eficiência energética", "bioenergia", "biomassa", \
                                "energia solar", "energia eólica", "pequenas centrais hidrelétricas", \
                                
                                # Agricultura e Meio Ambiente
                                "agricultura sustentável", "agroecologia", "agricultura de baixo carbono", \
                                "código florestal", "reserva legal", "área de preservação permanente", "app", \
                                "cadastro ambiental rural", "car", "programa de regularização ambiental", "pra", \
                                "cota de reserva ambiental", "cra", "sistema nacional de cadastro ambiental rural", \
                                
                                # Gestão Ambiental Empresarial
                                "sistema de gestão ambiental", "sga", "iso 14001", "política ambiental", \
                                "aspectos e impactos ambientais", "programa de monitoramento", \
                                "auditoria ambiental", "certificação ambiental", "análise de ciclo de vida", \
                                "pegada hídrica", "pegada ecológica", "ecoeficiência", \
                                
                                # Participação e Educação
                                "educação ambiental", "conscientização ambiental", "participação social", \
                                "consulta pública", "audiência pública ambiental", "conselho de meio ambiente", \
                                "ong ambiental", "movimento ambientalista", "ativismo ambiental", \
                                
                                # Instrumentos Econômicos
                                "pagamento por serviços ambientais", "psa", "icms ecológico", \
                                "taxa ambiental", "fundo ambiental", "financiamento ambiental", \
                                "seguro ambiental", "precificação ambiental", \
                                
                                # Riscos e Emergências Ambientais
                                "risco ambiental", "desastre ambiental", "emergência ambiental", \
                                "plano de emergência", "prevenção", "mitigação", "adaptação", \
                                "vulnerabilidade ambiental", "resiliência", \
                                
                                # Tecnologia e Inovação Ambiental
                                "tecnologia ambiental", "inovação verde", "cleantech", "biotecnologia ambiental", \
                                "sensoriamento remoto", "geoprocessamento", "sistema de informação geográfica", \
                                "sig", "monitoramento por satélite", "inteligência artificial ambiental"],
        "Política - Governo e Congresso Nacional": ["política", "governo", "congresso", "eleição", "eleições", "reeleição", "partido", "partidos", \
                                                    "ministro", "ministra", "presidente", "ex-presidente", "senado", "câmara", "deputado", "deputada", \
                                                    "senador", "senadora", "urnas", "executivo", "legislativo", "tse", "planalto", "primeira-dama", \
                                                    "casa civil", "inss", "fraude", "cpmi", "trama golpista", \
                                                    
                                                    # Presidentes e lideranças
                                                    "lula", "luiz inácio lula da silva", "bolsonaro", "jair bolsonaro", "dilma", "dilma rousseff", \
                                                    "temer", "michel temer", "fhc", "fernando henrique cardoso", "vice-presidente", "geraldo alckmin", \
                                                    
                                                    # Ministérios e órgãos do executivo
                                                    "ministério da fazenda", "fazenda", "ministério da educação", "ministério da saúde", \
                                                    "ministério do desenvolvimento", "ministério das relações exteriores", "itamaraty", \
                                                    "ministério da justiça", "ministério da defesa", "ministério da agricultura", \
                                                    "ministério de minas e energia", "ministério do trabalho", "ministério dos transportes", \
                                                    "ministério das comunicações", "ministério do meio ambiente", "ministério da cultura", \
                                                    "ministério do esporte", "ministério do turismo", "ministério da integração nacional", \
                                                    "ministério das cidades", "ministério da ciência e tecnologia", "secretaria-geral", \
                                                    "secretaria de governo", "advocacia-geral da união", "agu", "controladoria-geral da união", "cgu", \
                                                    
                                                    # Cargos e funções governamentais
                                                    "ministro de estado", "secretário executivo", "secretário nacional", "secretário especial", \
                                                    "assessor especial", "chefe de gabinete", "porta-voz", "secretário de imprensa", \
                                                    "diretor-geral", "presidente de autarquia", "superintendente", "coordenador", \
                                                    
                                                    # Poder legislativo
                                                    "congresso nacional", "senado federal", "câmara dos deputados", "assembleia legislativa", \
                                                    "câmara municipal", "vereador", "presidente do senado", "presidente da câmara", \
                                                    "mesa diretora", "liderança", "líder do governo", "líder da oposição", "bancada", \
                                                    "comissão", "relatoria", "relator", "parecer", "emenda", "substitutivo", \
                                                    
                                                    # Poder judiciário e órgãos de controle
                                                    "supremo tribunal federal", "stf", "superior tribunal de justiça", "stj", \
                                                    "tribunal superior eleitoral", "tribunal de contas da união", "tcu", \
                                                    "conselho nacional de justiça", "cnj", "ministério público federal", "mpf", \
                                                    "procuradoria-geral da república", "pgr", "polícia federal", "pf", \
                                                    
                                                    # Processos legislativos
                                                    "projeto de lei", "pl", "pec", "proposta de emenda constitucional", "medida provisória", "mp", \
                                                    "decreto", "portaria", "resolução", "instrução normativa", "ordem executiva", \
                                                    "lei complementar", "lei ordinária", "código", "estatuto", "regimento", \
                                                    "votação", "aprovação", "rejeição", "arquivamento", "tramitação", \
                                                    "plenário", "comissão", "audiência pública", "sessão", "reunião", \
                                                    
                                                    # Políticas públicas e programas
                                                    "política pública", "programa de governo", "plano nacional", "estratégia nacional", \
                                                    "política econômica", "política fiscal", "política monetária", "política social", \
                                                    "programa social", "transferência de renda", "auxílio", "benefício", \
                                                    "crédito subsidiado", "subsídio", "isenção", "redução de impostos", \
                                                    "crédito extraordinário", "orçamento", "loa", "ppa", "ldo", \
                                                    
                                                    # Relações internacionais
                                                    "diplomacia", "relações exteriores", "embaixada", "embaixador", "cônsul", \
                                                    "acordo internacional", "tratado", "convenção", "protocolo", "memorando", \
                                                    "cúpula", "reunião bilateral", "multilateral", "organização internacional", \
                                                    "tarifa", "tarifaço", "comércio internacional", "retaliação", "sanção", \
                                                    "guerra comercial", "estados unidos", "china", "união europeia", "mercosul", \
                                                    
                                                    # Economia e governo
                                                    "equipe econômica", "ministério da fazenda", "banco central", "bacen", \
                                                    "política fiscal", "arrecadação", "receita federal", "imposto", "tributo", \
                                                    "reforma tributária", "reforma administrativa", "reforma da previdência", \
                                                    "teto de gastos", "regra de ouro", "déficit", "superávit", "dívida pública", \
                                                    
                                                    # Partidos políticos
                                                    "pt", "partido dos trabalhadores", "psdb", "mdb", "pp", "pl", "psd", "republicanos", \
                                                    "dem", "pdt", "psol", "pcdo b", "avante", "solidariedade", "pode", "cidadania", \
                                                    "novo", "rede", "pv", "prtb", "dc", "pmu", "coligação", "federação partidária", \
                                                    
                                                    # Processos eleitorais
                                                    "eleições presidenciais", "eleições municipais", "eleições estaduais", \
                                                    "primeiro turno", "segundo turno", "campanha eleitoral", "propaganda eleitoral", \
                                                    "debate", "pesquisa eleitoral", "intenção de voto", "candidato", "candidatura", \
                                                    "registro de candidatura", "coligação eleitoral", "fundo eleitoral", \
                                                    "prestação de contas", "doação", "financiamento de campanha", \

                                                    # Corrupção e investigações
                                                    "operação lava jato", "lava jato", "operação car wash", "mensalão", "petrolão", \
                                                    "corrupção", "propina", "lavagem de dinheiro", "caixa dois", "enriquecimento ilícito", \
                                                    "investigação", "inquérito", "delação premiada", "colaboração premiada", \
                                                    "acordo de leniência", "multa", "ressarcimento", "confisco", "bloqueio de bens", \
                                                    
                                                    # Impeachment e crises políticas
                                                    "impeachment", "afastamento", "cassação", "renúncia", "licença", \
                                                    "crise política", "instabilidade", "governabilidade", "base aliada", \
                                                    "apoio político", "articulação política", "negociação", "acordo", \

                                                    # Comunicação governamental
                                                    "pronunciamento", "discurso", "entrevista coletiva", "nota oficial", \
                                                    "comunicado", "declaração", "posicionamento", "manifestação", \
                                                    "porta-voz", "assessoria de imprensa", "secretaria de comunicação", "secom", \
                                                    
                                                    # Eventos e cerimônias
                                                    "posse", "cerimônia de posse", "solenidade", "inauguração", \
                                                    "assinatura", "sanção", "promulgação", "publicação", "diário oficial", \
                                                    "agenda presidencial", "viagem oficial", "visita de estado", \
                                                    
                                                    # Orçamento e finanças públicas
                                                    "orçamento público", "receita", "gasto público", "investimento público", \
                                                    "emenda parlamentar", "emenda de bancada", "emenda individual", "emenda de comissão", \
                                                    "contingenciamento", "liberação de recursos", "repasse", \
                                                    "convênio", "termo de cooperação", \
                                                    
                                                    # Federalismo
                                                    "união", "estado", "município", "distrito federal", "governador", "prefeito", \
                                                    "secretário estadual", "secretário municipal", "pacto federativo", \
                                                    "descentralização", "municipalização", "estadualização", "competência", \
                                                    "cooperação técnica", "regime de colaboração", \
                                                    
                                                    # Controle e transparência
                                                    "transparência", "acesso à informação", "lei de acesso à informação", "lai", \
                                                    "portal da transparência", "prestação de contas", "accountability", \
                                                    "controle social", "participação popular", "consulta pública", \
                                                    "audiência pública", "ouvidoria", "corregedoria"],
        "Setor de Esportes": ["esporte", "futebol", "basquete", "vôlei", "atletismo", "olimpíadas", "copa", "campeonato", "clube", "jogador", \
                            "treinador", "partida", "competição", "cbf", "federação", "federações", "clubes", "atleta", "atletas", \
                            "arbitragem", "fifa", "xaud", "ednaldo", \
                            
                            # Modalidades Esportivas Principais
                            "futebol de campo", "futebol americano", "basquetebol", "voleibol", "handebol", "tênis", \
                            "natação", "ginástica", "judô", "boxe", "mma", "artes marciais", "caratê", "taekwondo", \
                            "esgrima", "levantamento de peso", "halterofilismo", "ciclismo", "maratona", \
                            "triathlon", "pentathlon", "decathlon", "salto", "arremesso", \
                            
                            # Esportes Aquáticos
                            "natação", "nado sincronizado", "polo aquático", "saltos ornamentais", "mergulho", \
                            "surfe", "vela", "remo", "canoagem", "rafting", "wakeboard", "esqui aquático", \
                            
                            # Esportes de Inverno
                            "esqui", "snowboard", "patinação no gelo", "hockey no gelo", "bobsled", "luge", \
                            "skeleton", "biathlon", "curling", \
                            
                            # Esportes Coletivos
                            "futebol de salão", "futsal", "beach soccer", "rugby", "futebol americano", \
                            "baseball", "softball", "cricket", "hockey", "lacrosse", \
                            
                            # Esportes Individuais
                            "tênis de mesa", "ping pong", "badminton", "squash", "golfe", "tiro", "tiro com arco", \
                            "hipismo", "equitação", "pentatlo moderno", \
                            
                            # Esportes Motorizados
                            "fórmula 1", "f1", "stock car", "motovelocidade", "motocross", "rally", "kartismo", \
                            "automobilismo", "motociclismo", "enduro", "trial", \
                            
                            # Esportes Paralímpicos
                            "paralimpíadas", "paraolimpíadas", "esporte paralímpico", "atleta paralímpico", \
                            "basquete em cadeira de rodas", "goalball", "boccia", "parabadminton", "para-atletismo", \
                            "para-natação", "para-ciclismo", "halterofilismo paralímpico", \
                            
                            # Competições e Eventos
                            "jogos olímpicos", "copa do mundo", "pan-americano", "sul-americano", \
                            "intercolegial", \
                            "liga", "série a", "série b", "divisão especial", "primeira divisão", "segunda divisão", \
                            "libertadores", "copa libertadores", "sul-americana", "champions league", "uefa", \
                            "copa américa", "eurocopa", "liga das nações", \
                            
                            # Organizações Esportivas Nacionais
                            "confederação brasileira de futebol", "cob", "comitê olímpico brasileiro", \
                            "cpb", "comitê paralímpico brasileiro", "confederação brasileira de basquete", "cbb", \
                            "confederação brasileira de voleibol", "cbv", "confederação brasileira de atletismo", "cbat", \
                            "confederação brasileira de natação", "cbda", "confederação brasileira de judô", "cbj", \
                            "confederação brasileira de tênis", "cbt", "confederação brasileira de handebol", "cbhb", \
                            
                            # Organizações Esportivas Internacionais
                            "comitê olímpico internacional", "coi", "world athletics", "fina", "fiba", \
                            "federação internacional de voleibol", "fivb", "international tennis federation", "itf", \
                            "federação internacional de judô", "ijf", "federação internacional de natação", \
                            
                            # Profissionais do Esporte
                            "preparador físico", "fisioterapeuta esportivo", "nutricionista esportivo", \
                            "psicólogo esportivo", "massagista", "scout", "olheiro", \
                            "comentarista esportivo", "narrador", "jornalista esportivo", "fotógrafo esportivo", \
                            
                            # Estrutura Esportiva
                            "estádio", "arena", "ginásio", "quadra", "campo", "piscina", "pista", "hipódromo", \
                            "kartódromo", "autódromo", "velódromo", "centro de treinamento", "ct", \
                            "base", "categoria de base", "peneira", \
                            
                            # Aspectos Médicos e Físicos
                            "lesão", "contusão", "reabilitação", \
                            "preparação física", \
                            "medicina esportiva", "fisiologia do exercício", "biomecânica", \
                            "doping", "exame antidoping", "substância proibida", "controle antidoping", \
                            
                            # Aspectos Comerciais
                            "naming rights", "direitos de transmissão", \
                            "marketing esportivo", \
                            "luvas", "bolsa atleta", \
                            
                            # Tecnologia no Esporte
                            "var", "video assistant referee", "hawk-eye", "goal line technology", \
                            "cronometragem eletrônica", "telemetria", "gps esportivo", \
                            "análise de performance", "big data esportivo", "inteligência artificial no esporte", \

                            # Aspectos Legais e Regulamentares
                            "fair play", "espírito esportivo", "código disciplinar", \
                            "tribunal de justiça desportiva", "tjd", "superior tribunal de justiça desportiva", "stjd", \
                            "lei pelé", "lei de incentivo ao esporte", "timemania", "loteria esportiva", \
                            
                            # Resultados e Estatísticas
                            "gol", "set", "game", "round", \
                            "tempo extra", "prorrogação", "pênaltis", "shootout", \
                            
                            # Eventos Específicos do Brasil
                            "jogos pan-americanos", "jogos sul-americanos", "olimpíadas escolares", \
                            "jogos escolares", "jogos universitários", "jogos abertos", "jogos regionais", \
                            "corrida de são silvestre", "maratona do rio", "iron man brasil", \
                            
                            # Esporte Educacional e Social
                            "esporte escolar", "educação física", "projeto social esportivo", \
                            "escolinha de esporte", "iniciação esportiva", "esporte de participação", \
                            "esporte de rendimento", "esporte educacional", "segunda via", "atleta cidadão", \
                            
                            # Transmissão e Mídia
                            "transmissão esportiva", "direitos de tv", "pay-per-view", "streaming esportivo", \
                            "sportv", "espn", "fox sports", "band sports", "premiere", \
                            "globo esporte", "esporte espetacular", "programa esportivo", \
                            
                            # Torcida e Público
                            "torcida", "torcedor", "torcida organizada", "arquibancada", \
                            "camarote", "ingresso", "bilheteria", \
                            "mando de campo", \
                            
                            # Esportes Emergentes
                            "e-sports", "esporte eletrônico", "crossfit", "parkour", "slackline", \
                            "stand up paddle", "sup", "kitesurf", "windsurf", "escalada", \
                            "rapel", "bungee jump", "skate", "bmx", "patins", \
                            
                            # Principais times de futebol do Rio de Janeiro, São Paulo e Minas Gerais
                            "flamengo", "vasco", "botafogo", "fluminense", "são paulo futebol clube", "palmeiras", \
                            "corinthians", "santos", "atlético mineiro", "cruzeiro", \

                            # Questões Sociais no Esporte
                            "racismo no esporte", "homofobia no esporte", "violência no esporte", \
                            "inclusão no esporte", "acessibilidade", "igualdade de gênero", \
                            "mulher no esporte", "esporte feminino", "lgbtqia+ no esporte"]                                                                                          

    }

    # ---------- INÍCIO: PRE-PROCESSAMENTO (descartar notícias por veículo) ----------
    # Regras por IdVeiculo (comparação em lowercase). Se um registro corresponder a qualquer regra,
    # ele será removido do DataFrame antes do restante do processamento.
    # Load the list of Valor columnists (used by IdVeiculo 10459 rule).
    # Embedding the list of Valor columnists directly into the code (avoids runtime file I/O)
    _COLUNISTAS_VALOR = {
        'alex ribeiro', 'amir labaki', 'ana inoue', 'ana maria diniz', 'andrea jubé',
        'armando castelar pinheiro', 'assis moreira', 'betania tanure', 'bruno carazza',
        'catherine vieira', 'césar felício', 'claudia safatle', 'claudio garcia',
        'daniela cachich', 'daniela chiaretti', 'edvaldo santana', 'fernando exman',
        'fernando torres', 'gustavo loyola', 'humberto saccomandi', 'isabel clemente',
        'isis borge', 'jairo saddi', 'joaquim levy', 'jorge arbache', 'jorge lucki',
        'josé de souza martins', 'josé eli da veiga', 'josé júlio senna', 'luiz gonzaga belluzzo',
        'luiz schymura', 'marcelo cardoso', 'marcelo d’agosto', 'márcio garcia',
        'maria clara r. m. do prado', 'maria cristina fernandes', 'mariana clark',
        'mario mesquita', 'marli olmos', 'michel laub', 'naercio menezes filho',
        'nilson teixeira', 'pedro butcher', 'pedro cafardo', 'pedro cavalcanti e renato fragelli',
        'rafael souto', 'renato bernhoeft', 'robinson borges', 'sergio chaia',
        'sergio lamucci', 'stela campos', 'tatiana salem levy', 'tiago cavalcanti',
        'vicky bloch', 'viviane martins'
    }


    def _should_discard_row(row):
        try:
            idv = row.get('IdVeiculo', None)
        except Exception:
            idv = None

        titulo = '' if pd.isna(row.get('Titulo', '')) else str(row.get('Titulo', '')).strip().lower()
        conteudo = '' if pd.isna(row.get('Conteudo', '')) else str(row.get('Conteudo', '')).strip().lower()

        # Build first N lines lists
        lines = [l.strip() for l in (conteudo.splitlines() if conteudo else [])]

        def any_line_eq(word, n):
            if not lines:
                return False
            lim = min(len(lines), n)
            for i in range(lim):
                if lines[i] == word:
                    return True
            return False

        def any_line_startswith(prefix, n):
            if not lines:
                return False
            lim = min(len(lines), n)
            for i in range(lim):
                if lines[i].startswith(prefix):
                    return True
            return False

        # Build combined text for checks that should look everywhere in the article
        texto_completo = (titulo + ' ' + conteudo).strip()

        # Vehicle-specific rules (all comparisons made in lowercase)
        if idv == 331:
            if any_line_eq('análise', 10):
                return True
            if any_line_eq('opinião', 10):
                return True
            # New rules: exact single-word / single-line markers that should trigger discard
            if any_line_eq('erramos', 10):
                return True
            if any_line_eq('painel do leitor', 10):
                return True
            if any_line_eq('mortes', 10):
                return True
            if any_line_eq('tendências/debates', 10) or any_line_eq('tendências / debates', 10):
                return True
            if any_line_eq('réplica', 10):
                return True
            if titulo == 'expediente' or any_line_eq('expediente', 5):
                return True

        if idv == 10459:
            if any_line_eq('análise', 10):
                return True
            if any_line_eq('opinião jurídica', 10):
                return True
            if any_line_eq('opinião', 10):
                return True
            if titulo == 'expediente' or any_line_eq('expediente', 5):
                return True

            # Discard if any known Valor columnist name appears anywhere in the text
            if _COLUNISTAS_VALOR:
                # Check for any columnist name as a substring in the combined text
                for nome in _COLUNISTAS_VALOR:
                    if nome in texto_completo:
                        return True

        if idv == 682:
            if titulo == 'expediente' or any_line_eq('expediente', 5):
                return True
            if any_line_eq('análise', 15):
                return True
            if any_line_eq('opinião', 15):
                return True
            # New rules
            if any_line_eq('mensagens cartas@oglobo.com.br', 10):
                return True
            if any_line_eq('*artigo', 10):
                return True
            if any_line_eq('artigo', 10):
                return True
            if 'oglobo.globo.com/opinião' in texto_completo:
                return True
            if titulo == 'falecimentos':
                return True

        if idv == 675:
            if any_line_eq('espaço aberto', 10):
                return True
            if any_line_startswith('notas e informações', 10):
                return True
            if titulo == 'expediente':
                return True
            # New rules for 675
            if titulo == 'obituário' or titulo == 'falecimentos':
                return True
            if any_line_startswith('artigo', 10):
                return True

        return False

    # Execute the pre-processing discard step and log summary
    try:
        if 'IdVeiculo' in df.columns and 'Conteudo' in df.columns:
            initial_count = len(df)
            mask_discard = df.apply(_should_discard_row, axis=1)
            num_discarded = int(mask_discard.sum())
            if num_discarded > 0:
                # Provide a total and breakdown by IdVeiculo for easier auditing
                discarded_ids = df.loc[mask_discard, 'IdVeiculo']
                breakdown = discarded_ids.value_counts().to_dict()
                print(f"🧹 Pré-processamento: descartando {num_discarded} notícias por regras de veículo (de {initial_count})")
                print(f"   ↳ Descartes por IdVeiculo: {breakdown}")
                # Optionally save the discarded rows for audit/debug (commented)
                # df[mask_discard].to_csv('dados/api/discarded_prompts_setor.csv', index=False)
            df = df[~mask_discard].copy()
    except Exception as e:
        print(f"⚠️ Erro no pré-processamento de descarte: {e}")

    # ---------- FIM: PRE-PROCESSAMENTO ----------

    # Definir os IDs dos veículos prioritários
    veiculos_prioritarios = [10459, 675]
    pontuacao_extra_veiculo = 10 # Pontuação extra para notícias desses veículos (ajuste este valor se necessário)
    # Bônus quando o campo 'Paginas' contiver o marcador '_01_001'
    pontuacao_extra_pagina = 10  # Ajuste este valor conforme necessário

    def calculate_relevance_score(text, id_veiculo, temas_termos, veiculos_prioritarios, pontuacao_extra_veiculo, paginas_value=None, pontuacao_extra_pagina=0):
        """
        Calcula uma pontuação de relevância para a notícia.
        A pontuação é baseada na frequência dos termos chave dos temas, no tamanho do texto
        e em uma pontuação extra para veículos prioritários.
        Retorna a pontuação de relevância e o tema preponderante.
        """
        text_lower = text.lower()
        theme_counts = Counter()
        total_term_count = 0
        
        # Criar uma única regex por tema
        for tema, termos in temas_termos.items():
            # Combinar todos os termos em uma única regex
            pattern = r'\b(?:' + '|'.join(re.escape(termo) for termo in termos) + r')\b'
            matches = re.findall(pattern, text_lower)
            count = len(matches)
            theme_counts[tema] = count
            total_term_count += count  # ← ESSENCIAL: somar ao total
        
        # Remover temas com contagem zero para identificar o tema preponderante
        theme_counts_filtered = {tema: count for tema, count in theme_counts.items() if count > 0}

        preponderant_theme = None
        if theme_counts_filtered:
            preponderant_theme = max(theme_counts_filtered, key=theme_counts_filtered.get)

        # Calcular a pontuação total de relevância (contagem de termos)
        relevance_score = total_term_count

        # Aplicar bônus por veículo prioritário (se aplicável)
        try:
            # id_veiculo pode ser int ou string; tente converter para int quando possível
            if id_veiculo is not None:
                try:
                    vid = int(id_veiculo)
                except Exception:
                    vid = id_veiculo

                if vid in veiculos_prioritarios:
                    relevance_score += pontuacao_extra_veiculo
        except Exception:
            # Falha silenciosa: não adicionar o bônus se houver problemas inesperados
            pass

        # Aplicar bônus se o campo 'Paginas' contiver o marcador específico
        try:
            if paginas_value is not None:
                paginas_str = str(paginas_value)
                if '_01_001' in paginas_str:
                    relevance_score += pontuacao_extra_pagina
        except Exception:
            pass

        return relevance_score, preponderant_theme

    # Aplicar a função para calcular a pontuação e identificar o tema preponderante
    results = df.apply(lambda row: calculate_relevance_score(row['TextoCompleto'], row['IdVeiculo'], temas_termos, veiculos_prioritarios, pontuacao_extra_veiculo), axis=1)

    # Separar os resultados em novas colunas
    df['RelevanceScore'], df['TemaPreponderante'] = zip(*results)

    # ========================================
    # BÔNUS DE 100 PONTOS PARA TERMOS NO TÍTULO
    # ========================================
    
    print("Aplicando bônus de 100 pontos para termos específicos no título...")
    
    # Lista de termos que garantem bônus de 100 pontos quando aparecem no título
    termos_bonus = [
        "aves", "bezerro", "boi", "bovina", "carne", "carnes", "frango", "gado", 
        "gripe aviária", "suína", "abpa", "ministério da agricultura e pecuária", 
        "mapa", "alunos", "educação", "ensino médio", "energia", "inflação", 
        "juro", "juros", "tarifaço", "varejo", "vendas", "descarbonização", 
        "amazônia", "camada de ozônio", "cop30", "ibama", "política climática", 
        "mineração", "câmara", "centro", "direita", "esquerda", "ex-presidente", 
        "governo", "lula", "presidente", "tarcísio",
        # inclusões em 10/11/25 - início
        "agricultores", "agro", "fertilizantes", # inclusões em 10/11/25 Agro
        "aneel",
        "Drex", "itaú", "imposto de renda",
        "judiciário",
        "ambiental", "aquecimento", "climático", "efeito estufa", "gases",
        "pt", "Trump"
        # inclusões em 10/11/25 - fim
    ]
    
    def verificar_bonus_titulo(titulo):
        """Verifica se o título contém algum dos termos que garantem bônus"""
        if pd.isna(titulo):
            return False
        titulo_lower = titulo.lower()
        for termo in termos_bonus:
            if re.search(r'\b' + re.escape(termo.lower()) + r'\b', titulo_lower):
                return True
        return False
    
    # Aplicar o bônus de 100 pontos
    df['TemBonusTitulo'] = df['Titulo'].apply(verificar_bonus_titulo)
    df.loc[df['TemBonusTitulo'], 'RelevanceScore'] += 100
    
    # Informar quantas notícias receberam o bônus
    num_noticias_com_bonus = df['TemBonusTitulo'].sum()
    print(f"✓ {num_noticias_com_bonus} notícias receberam bônus de 100 pontos no título")
    
    # ========================================
    # FIM DO BÔNUS
    # ========================================


    # Salvar o DataFrame completo com RelevanceScore
    print("Salvando o DataFrame com RelevanceScore..." )
    df.to_excel(arq_relevance_score_setor, index=False)

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
        "Política - Governo e Congresso Nacional": qt_politica,
        "Setor de Finanças": qt_financas,
        "Justiça": qt_justica,
        "Setor de Agronegócios": qt_agro
    }

    df_top_noticias_list = []

    # Selecionar as top notícias dos temas prioritários
    for tema, qtd in temas_prioritarios.items():
        df_tema = df_relevante[df_relevante['TemaPreponderante'] == tema].sort_values(by='RelevanceScore', ascending=False)
        df_top_noticias_list.append(df_tema.head(qtd))

    # Filtrar os temas restantes
    temas_restantes = [tema for tema in df_relevante['TemaPreponderante'].unique() if tema not in temas_prioritarios]
    df_restantes = df_relevante[df_relevante['TemaPreponderante'].isin(temas_restantes)].copy()

    # Selecionar as top demais notícias dos temas restantes
    if not df_restantes.empty:
        df_restantes_sorted = df_restantes.sort_values(by='RelevanceScore', ascending=False)
        df_top_noticias_list.append(df_restantes_sorted.head(qt_demais))

        # Incluir a notícia mais bem pontuada de setores em lista_setores que ainda não tiveram nenhuma notícia selecionada
        # Correção de inclusão de setores vazios
        # Concatenar notícias inicialmente selecionadas
        df_top_noticias = pd.concat(df_top_noticias_list, ignore_index=True)

        # Verificar setores totalmente vazios e incluir a melhor notícia de cada
        contagem_por_setor = df_top_noticias['TemaPreponderante'].value_counts().to_dict()
        for setor in lista_setores:
            if contagem_por_setor.get(setor, 0) == 0:
                df_setor = df_relevante[df_relevante['TemaPreponderante'] == setor]
                if not df_setor.empty:
                    noticia_top = df_setor.sort_values(by='RelevanceScore', ascending=False).head(1)
                    df_top_noticias_list.append(noticia_top)
                    print(f"Adicionando a melhor notícia do setor '{setor}' com ID {noticia_top['Id'].values[0]}")

        # Atualizar df_top_noticias após incluir setores vazios
        df_top_noticias = pd.concat(df_top_noticias_list, ignore_index=True)
    
        contagem_por_setor = {}
        if 'df_top_noticias' in locals():
            contagem_por_setor = df_top_noticias['TemaPreponderante'].value_counts().to_dict()
        
        contagem_por_setor = df_top_noticias['TemaPreponderante'].value_counts().to_dict()
        for setor in lista_setores:
            if contagem_por_setor.get(setor, 0) == 0:
                df_setor = df_relevante[df_relevante['TemaPreponderante'] == setor]
                if not df_setor.empty:
                    noticia_top = df_setor.sort_values(by='RelevanceScore', ascending=False).head(1)
                    df_top_noticias_list.append(noticia_top)
                    print(f"Adicionando a melhor notícia do setor '{setor}' com ID {noticia_top['Id'].values[0]}")
        # Fim do ajuste
        setores_selecionados = set(df_top_noticias['TemaPreponderante'].unique()) if 'df_top_noticias' in locals() else set()
        for setor in lista_setores:
            if setor not in setores_selecionados:
                df_setor = df_relevante[df_relevante['TemaPreponderante'] == setor]
                if not df_setor.empty:
                    noticia_top = df_setor.sort_values(by='RelevanceScore', ascending=False).head(1)
                    df_top_noticias_list.append(noticia_top)
                    print(f"Adicionando a melhor notícia do setor '{setor}' com ID {noticia_top['Id'].values[0]}")

    # Concatenar todos os DataFrames das notícias selecionadas
    df_top_noticias = pd.concat(df_top_noticias_list, ignore_index=True)

    # 6. Criar prompts para cada notícia selecionada

    # Dicionário de mapeamento dos temas
    mapeamento_temas = {
        "Setor de Papel e Celulose": "PAPEL E CELULOSE",
        "Setor de Mineração": "MINERAÇÃO",
        "Setor de Agronegócios": "AGRONEGÓCIOS",
        "Setor de Educação": "EDUCAÇÃO",
        "Setor de Energia": "ENERGIA",
        "Setor de Finanças": "FINANÇAS",
        "Setor de Óleo de Gás": "ÓLEO E GÁS",
        "Justiça": "JUSTIÇA",
        "Meio Ambiente e ESG": "MEIO AMBIENTE E ESG",
        "Política - Governo e Congresso Nacional": "POLÍTICA",
        "Setor de Esportes": "ESPORTES"
    }

    prompts = []
    for index, row in df_top_noticias.iterrows():
        texto_noticia = row['TextoCompleto']
        tema_preponderante = row['TemaPreponderante']
        ids_noticia = str(row['Id']) # ID da notícia
        relevance_score = row['RelevanceScore'] # Obter a pontuação de relevância
        id_veiculo_noticia = row['IdVeiculo'] # Obter o IdVeiculo da notícia

        # Aplicar o mapeamento do tema
        tema_formatado = mapeamento_temas.get(tema_preponderante, tema_preponderante)

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
            "Tema": tema_formatado, # Usar o tema formatado
            "RelevanceScore": relevance_score, # Adicionar a pontuação de relevância
            "IdVeiculo": id_veiculo_noticia # Adicionar o IdVeiculo
        })

    # 7. Salva em Excel
    df_prompts = pd.DataFrame(prompts)

    # Ordenar por tema para melhor organização (ou pela ordem que preferir para o arquivo de saída)
    df_prompts = df_prompts.sort_values(by='Tema')

    #df_prompts.to_excel(arq_prompts_setor, index=False)
    #print("Arquivo salvo: ", arq_prompts_setor)
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    print(f"Tempo de processamento da rotina prompts_setor: {minutes:02d}:{seconds:02d} (mm:ss) ({elapsed_time:.2f} segundos)")
    return df_prompts