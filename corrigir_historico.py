import requests
import time
import os
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do ficheiro .env para o ambiente

# Lê as variáveis do ambiente (seja do .env local ou do servidor na nuvem)
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')
HUBSPOT_PORTAL_ID = os.environ.get('HUBSPOT_PORTAL_ID')
ID_ETAPA_RESOLVIDO = "1067263045"

# --- Funções Reutilizadas e Adaptadas ---

def find_original_ticket_historico(ticket_a_verificar, properties_to_match):
    """Busca por um ticket original que seja MAIS ANTIGO que o ticket atual."""
    search_url = "https://api.hubapi.com/crm/v3/objects/tickets/search"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}

    filters = [
        {"propertyName": "hs_object_id", "operator": "NEQ", "value": ticket_a_verificar['id']},
        {"propertyName": "createdate", "operator": "LT", "value": ticket_a_verificar['properties']['createdate']},
        {"propertyName": "rc__marca", "operator": "EQ", "value": properties_to_match["rc__marca"]},
        {"propertyName": "rc__tipo_de_solicitacao", "operator": "EQ", "value": properties_to_match["rc__tipo_de_solicitacao"]},
        #{"propertyName": "submotivo_do_contato", "operator": "EQ", "value": properties_to_match["submotivo_do_contato"]},
        {"propertyName": "e_mail_do_aluno", "operator": "EQ", "value": properties_to_match["e_mail_do_aluno"]},
        {"propertyName": "hs_pipeline_stage", "operator": "NEQ", "value": ID_ETAPA_RESOLVIDO},
    ]

    query = {"filterGroups": [{"filters": filters}], "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}], "limit": 1}
    
    response = requests.post(search_url, headers=headers, json=query)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None

def update_duplicate_ticket_info(duplicate_ticket_id, original_ticket_id):
    """Atualiza o ticket duplicado."""
    update_url = f"https://api.hubapi.com/crm/v3/objects/tickets/{duplicate_ticket_id}"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}
    original_ticket_url = f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{original_ticket_id}"
    
    payload = {"properties": {"status_da_duplicata": "Pronto para mesclar", "link_para_o_ticket_original": original_ticket_url}}
    
    print(f"  -> CORRIGINDO TICKET #{duplicate_ticket_id} para ser duplicata de #{original_ticket_id}")
    response = requests.patch(update_url, headers=headers, json=payload)
    response.raise_for_status()

def get_all_open_tickets_para_correcao():
    """Busca todos os tickets que não estão resolvidos, ignorando se já foram processados."""
    all_tickets = []
    after = None
    url = "https://api.hubapi.com/crm/v3/objects/tickets/search"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}
    
    # A LÓGICA DE IGNORAR FOI REMOVIDA DESTA BUSCA
    query = {
        "filterGroups": [{
            "filters": [
                {"propertyName": "hs_pipeline", "operator": "EQ", "value": "732696496"},
                {"propertyName": "hs_pipeline_stage", "operator": "NEQ", "value": ID_ETAPA_RESOLVIDO}
            ]
        }],
        "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
        "properties": ["rc__marca", "rc__tipo_de_solicitacao", "e_mail_do_aluno", "createdate"],
        "limit": 100
    }

    while True:
        if after: query["after"] = after
        
        print(f"Buscando uma página de tickets abertos para correção...")
        response = requests.post(url, headers=headers, json=query)
        response.raise_for_status()
        data = response.json()
        
        all_tickets.extend(data.get("results", []))
        
        if "paging" in data and "next" in data["paging"]:
            after = data["paging"]["next"]["after"]
            time.sleep(0.5)
        else:
            break

    return all_tickets

# --- Bloco de Execução Principal ---
if __name__ == '__main__':
    print("--- INICIANDO SCRIPT DE CORREÇÃO DE TICKETS HISTÓRICOS ---")
    
    tickets_a_processar = get_all_open_tickets_para_correcao()
    total_tickets = len(tickets_a_processar)
    print(f"Total de {total_tickets} tickets abertos encontrados para re-análise.")

    for index, ticket in enumerate(tickets_a_processar):
        ticket_id = ticket['id']
        properties = ticket.get("properties", {})
        
        print(f"\n({index + 1}/{total_tickets}) Re-analisando Ticket #{ticket_id}...")

        properties_to_match = {
            "rc__marca": properties.get("rc__marca"),
            "rc__tipo_de_solicitacao": properties.get("rc__tipo_de_solicitacao"),
            #"submotivo_do_contato": properties.get("submotivo_do_contato"),
            "e_mail_do_aluno": properties.get("e_mail_do_aluno")
        }

        if not all(properties_to_match.values()):
            print("  -> Ignorando ticket por falta de dados para comparação.")
            continue

        try:
            original_ticket = find_original_ticket_historico(ticket, properties_to_match)
            
            if original_ticket:
                original_id = original_ticket['id']
                update_duplicate_ticket_info(ticket_id, original_id)
            else:
                
                print("  -> Nenhuma duplicata encontrada. Este é um ticket original.")
            
            time.sleep(0.5)

        except Exception as e:
            print(f"  -> Ocorreu um erro ao processar o ticket #{ticket_id}: {e}")

    print("\n--- CORREÇÃO DE TICKETS HISTÓRICOS CONCLUÍDA ---")