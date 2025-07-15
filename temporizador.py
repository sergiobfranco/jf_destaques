import datetime

def aguardar_data_futura():
    while True:
        try:
            data_input = input("Digite a data e hora futura no formato AAAA-MM-DD HH:MM:SS: ")
            data_futura = datetime.datetime.strptime(data_input, "%Y-%m-%d %H:%M:%S")
            agora = datetime.datetime.now()
            segundos_a_esperar = (data_futura - agora).total_seconds()

            if segundos_a_esperar < 0:
                print("A data e hora futuras especificadas já passaram.")
                continuar = input("Deseja continuar mesmo assim? (s/n): ").strip().lower()
                if continuar != 's':
                    continue
            print(f"Início do processamento: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            break

        except ValueError:
            print("Formato inválido. Use o formato AAAA-MM-DD HH:MM:SS.")

    return segundos_a_esperar
