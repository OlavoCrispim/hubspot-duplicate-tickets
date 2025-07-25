import requests
import json
import os
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do ficheiro .env para o ambiente

# Lê as variáveis do ambiente (seja do .env local ou do servidor na nuvem)
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')
HUBSPOT_PORTAL_ID = os.environ.get('HUBSPOT_PORTAL_ID')

# --- SCRIPT DE DIAGNÓSTICO ---
def get_ticket_properties(ticket_id):
    """Busca um ticket e imprime todas as suas propriedades."""

    # O URL para buscar um único ticket por ID
    url = f"https://api.hubapi.com/crm/v3/objects/tickets/{ticket_id}"

    # Precisamos de especificar todas as propriedades que queremos ver
    params = {
        "properties": "subject,hs_pipeline_stage,rc__marca,rc__tipo_de_solicitacao,submotivo_do_contato,e_mail_do_aluno"
    }

    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        print(f"\nBuscando propriedades para o Ticket ID: {ticket_id}...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # Lança um erro se a API falhar

        data = response.json()

        print("\n--- PROPRIEDADES RECEBIDAS DA API ---")
        # Imprime os dados de forma legível
        print(json.dumps(data.get('properties'), indent=2))
        print("\n------------------------------------")

    except Exception as e:
        print(f"\nOcorreu um erro: {e}")

if __name__ == '__main__':
    print("--- Ferramenta de Diagnóstico de Propriedades do HubSpot ---")

    test_ticket_id = input("Por favor, insira o ID de um ticket recente que tenha o campo 'Submotivo do contato' preenchido: ")

    if test_ticket_id:
        get_ticket_properties(test_ticket_id)
    else:
        print("Nenhum ID de ticket inserido. A sair.")