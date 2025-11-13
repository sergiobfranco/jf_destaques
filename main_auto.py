import sys
import datetime
from main_auto_exec import main_exec

def processar_relatorio(tipo_relatorio):
    """
    Função principal que processa o relatório baseado no tipo
    """
    print(f"Iniciando processamento do relatório: {tipo_relatorio}")
    print(f"Timestamp: {datetime.datetime.now()}")
    
    try:
        if tipo_relatorio == "completo":
            # Sua lógica atual do relatório completo
            print("Processando relatório COMPLETO...")
            main_exec()
            # ... seu código atual aqui ...
            
        elif tipo_relatorio == "estadao":
            # Lógica específica para Estadão
            print("Processando relatório ESTADÃO...")
            # ... código específico para Estadão ...
            
        elif tipo_relatorio == "folha":
            # Lógica específica para Folha
            print("Processando relatório FOLHA...")
            # ... código específico para Folha ...
            
        elif tipo_relatorio == "valor":
            # Lógica específica para Valor
            print("Processando relatório VALOR...")
            # ... código específico para Valor ...
            
        elif tipo_relatorio == "globo":
            # Lógica específica para Globo
            print("Processando relatório GLOBO...")
            # ... código específico para Globo ...
            
        else:
            raise ValueError(f"Tipo de relatório inválido: {tipo_relatorio}")
            
        print(f"Relatório {tipo_relatorio} processado com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro ao processar relatório {tipo_relatorio}: {str(e)}")
        return False

def main():
    """
    Função principal que recebe argumentos da linha de comando
    """
    # Verificar se foi passado um parâmetro
    if len(sys.argv) < 2:
        print("Erro: Tipo de relatório não especificado")
        print("Uso: python main_auto.py [completo|estadao|folha|valor|globo]")
        sys.exit(1)
    
    tipo_relatorio = sys.argv[1].lower()  # Pegar o primeiro argumento
    
    # Validar o tipo de relatório
    tipos_validos = ["completo", "estadao", "folha", "valor", "globo"]
    if tipo_relatorio not in tipos_validos:
        print(f"Erro: Tipo de relatório inválido: {tipo_relatorio}")
        print(f"Tipos válidos: {', '.join(tipos_validos)}")
        sys.exit(1)
    
    # Processar o relatório
    sucesso = processar_relatorio(tipo_relatorio)
    
    if sucesso:
        print("Processamento finalizado com sucesso!")
        sys.exit(0)
    else:
        print("Processamento finalizado com erro!")
        sys.exit(1)

if __name__ == "__main__":
    main()