# Importando as ferramentas necessárias
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do ficheiro .env para o ambiente

# Lê as variáveis do ambiente (seja do .env local ou do servidor na nuvem)
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')
HUBSPOT_PORTAL_ID = os.environ.get('HUBSPOT_PORTAL_ID')

app = Flask(__name__)

def find_original_ticket(new_ticket_id, properties_to_match):
    """Busca por um ticket original com base nas regras de negócio definidas."""
    search_url = "https://api.hubapi.com/crm/v3/objects/tickets/search"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }

    thirty_days_ago = datetime.now() - timedelta(days=30)
    timestamp_ms = int(thirty_days_ago.timestamp() * 1000)

    # CORREÇÃO FINAL: Garantindo que a sintaxe da lista está 100% correta
    filters = [
        {"propertyName": "hs_object_id", "operator": "NEQ", "value": new_ticket_id},
        {"propertyName": "rc__marca", "operator": "EQ", "value": properties_to_match["rc__marca"]},
        {"propertyName": "rc__tipo_de_solicitacao", "operator": "EQ", "value": properties_to_match["rc__tipo_de_solicitacao"]},
        #{"propertyName": "submotivo_do_contato", "operator": "EQ", "value": properties_to_match["submotivo_do_contato"]},
        {"propertyName": "e_mail_do_aluno", "operator": "EQ", "value": properties_to_match["e_mail_do_aluno"]},
        {"propertyName": "hs_pipeline_stage", "operator": "NEQ", "value": "1067263045"},
        {"propertyName": "createdate", "operator": "GTE", "value": timestamp_ms}
    ]

    query = {
        "filterGroups": [{"filters": filters}],
        "sorts": [{"propertyName": "createdate", "direction": "ASCENDING"}],
        "limit": 1
    }

    #print(f"DEBUG: Enviando a seguinte query para o HubSpot: {query}")
    response = requests.post(search_url, headers=headers, json=query)
    response.raise_for_status()

    results = response.json().get("results", [])
    return results[0] if results else None

def update_duplicate_ticket_info(duplicate_ticket_id, original_ticket_id):
    update_url = f"https://api.hubapi.com/crm/v3/objects/tickets/{duplicate_ticket_id}"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}
    original_ticket_url = f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}/ticket/{original_ticket_id}"
    
    # !! VERIFIQUE E CORRIJA OS NOMES INTERNOS DAS SUAS PROPRIEDADES PERSONALIZADAS AQUI TAMBÉM !!
    payload = {
        "properties": {
            # Substitua 'NOME_INTERNO_STATUS_DUPLICATA' pelo nome interno da sua propriedade "Status da Duplicata"
            "status_da_duplicata": "Pronto para mesclar",
            
            # Substitua 'NOME_INTERNO_LINK_TICKET' pelo nome interno da sua propriedade "Link para o Ticket Original"
            "link_para_o_ticket_original": original_ticket_url
        }
    }
    
    print(f"Atualizando ticket duplicado {duplicate_ticket_id}...")
    response = requests.patch(update_url, headers=headers, json=payload)
    response.raise_for_status()
    print("Ticket atualizado com sucesso!")

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    print("\n--- Novo webhook recebido ---")
    data = request.get_json()
    print(f"Payload recebido: {data}")

    if not data: return jsonify({"status": "erro", "mensagem": "Payload vazio"}), 400

    new_ticket_id = data.get("hs_ticket_id")
    properties_to_match = {
        "rc__marca": data.get("rc__marca"),
        "rc__tipo_de_solicitacao": data.get("rc__tipo_de_solicitacao"),
        #"submotivo_do_contato": data.get("submotivo_do_contato"),
        "e_mail_do_aluno": data.get("e_mail_do_aluno")
    }

    if not all(properties_to_match.values()) or not new_ticket_id:
        print("ERRO: Dados insuficientes no payload.")
        return jsonify({"status": "erro", "mensagem": "Dados insuficientes"}), 400

    try:
        original_ticket = find_original_ticket(new_ticket_id, properties_to_match)
        if original_ticket:
            original_ticket_id = original_ticket['id']
            print(f"DUPLICADO ENCONTRADO! O ticket original é o #{original_ticket_id}.")
            update_duplicate_ticket_info(new_ticket_id, original_ticket_id)
        else:
            print("Nenhum duplicado encontrado. Ticket é único.")
        return jsonify({"status": "sucesso"}), 200
    except Exception as e:
        print(f"ERRO INESPERADO: {e}")
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == '__main__':
    print("Iniciando servidor de teste...")
    app.run(port=5000, debug=True)