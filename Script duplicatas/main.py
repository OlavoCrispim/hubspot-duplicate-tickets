# Ficheiro: main.py
import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

# As chaves são lidas de variáveis de ambiente, que serão configuradas no Cloud Run
HUBSPOT_API_KEY = os.environ.get('HUBSPOT_API_KEY')
HUBSPOT_PORTAL_ID = os.environ.get('HUBSPOT_PORTAL_ID')
ID_ETAPA_RESOLVIDO = "1067263045" # O ID da sua etapa "Resolvido / Fechado"

app = Flask(__name__)

def find_original_ticket(new_ticket_id, properties_to_match):
    """Busca por um ticket original com base nas regras de negócio definidas."""
    search_url = "https://api.hubapi.com/crm/v3/objects/tickets/search"
    headers = {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    timestamp_ms = int(thirty_days_ago.timestamp() * 1000)

    filters = [
        {"propertyName": "hs_object_id", "operator": "NEQ", "value": new_ticket_id},
        {"propertyName": "rc__marca", "operator": "EQ", "value": properties_to_match["rc__marca"]},
        {"propertyName": "rc__tipo_de_solicitacao", "operator": "EQ", "value": properties_to_match["rc__tipo_de_solicitacao"]},
        #{"propertyName": "submotivo_do_contato", "operator": "EQ", "value": properties_to_match["submotivo_do_contato"]},
        {"propertyName": "e_mail_do_aluno", "operator": "EQ", "value": properties_to_match["e_mail_do_aluno"]},
        {"propertyName": "hs_pipeline_stage", "operator": "NEQ", "value": ID_ETAPA_RESOLVIDO},
        {"propertyName": "createdate", "operator": "GTE", "value": timestamp_ms}
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
    response = requests.patch(update_url, headers=headers, json=payload)
    response.raise_for_status()
    print(f"Ticket {duplicate_ticket_id} atualizado com sucesso.")

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    data = request.get_json()
    if not data: return jsonify({"status": "erro", "mensagem": "Payload vazio"}), 400

    new_ticket_id = data.get("hs_ticket_id")
    properties_to_match = {
        "rc__marca": data.get("rc__marca"),
        "rc__tipo_de_solicitacao": data.get("rc__tipo_de_solicitacao"),
        #"submotivo_do_contato": data.get("submotivo_do_contato"),
        "e_mail_do_aluno": data.get("e_mail_do_aluno")
    }

    if not all(properties_to_match.values()) or not new_ticket_id:
        return jsonify({"status": "erro", "mensagem": "Dados insuficientes"}), 400

    try:
        original_ticket = find_original_ticket(new_ticket_id, properties_to_match)
        if original_ticket:
            original_ticket_id = original_ticket['id']
            update_duplicate_ticket_info(new_ticket_id, original_ticket_id)
        else:
            print("Nenhum duplicado encontrado.")
        return jsonify({"status": "sucesso"}), 200
    except Exception as e:
        print(f"ERRO INESPERADO: {e}")
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)