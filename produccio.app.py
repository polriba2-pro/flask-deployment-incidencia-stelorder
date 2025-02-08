import sys
import io
from flask import Flask, request, jsonify
import requests
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__)

app.config['JSON_AS_ASCII'] = False  # Evita errors de codificació ASCII


# Configuració: API Key i Headers per fer les peticions a les APIs externes.
API_KEY = "qU8vY9cwt1ve8hK5lOgQGB8KjCnSOcvtTwD7FJJW"
HEADERS = {
    "apikey": API_KEY,
    "Accept": "application/json"
}

# URLs externes per accedir a les dades
CLIENTS_URL = "https://app.stelorder.com/app/clients"      # API de clients
INCIDENTS_URL = "https://app.stelorder.com/app/incidents"  # API d'incidències

@app.route('/webhook', methods=['POST'])
def webhook():
    """ Rep una petició de Retell AI amb un DNI i processa la informació. """
    
    # 📌 Captura les dades en RAW
    raw_data = request.get_data(as_text=True).encode('utf-8')  # Forçar codificació UTF-8
    print("\n🔍 RAW JSON REBUT AL SERVIDOR:\n", raw_data, "\n")

    try:
        # 📌 Intentem convertir el JSON rebut
        data = json.loads(raw_data)
        print("\n✅ JSON CONVERTIT A DICCIONARI:", data, "\n")
    except json.JSONDecodeError as e:
        print("❌ Error de format JSON:", str(e))
        return jsonify({"error": "Error en el format JSON rebut"}), 400
 

    dni = data.get("args", {}).get("DNI")


    if not dni:
        print("❌ No s'ha trobat 'dni' dins el JSON:", data)
        return jsonify({"error": "Falta el paràmetre 'dni' en la petició 22"}), 400

    print("✅ DNI rebut:", dni)

    # 3️⃣ Consultem l'API de clients per obtenir la llista de clients
    try:
        response_clients = requests.get(CLIENTS_URL, headers=HEADERS)
        response_clients.raise_for_status()
        clients = response_clients.json()
    except requests.exceptions.RequestException as e:
        print("⚠️ Error en obtenir clients:", e)
        return jsonify({"error": "Error en obtenir clients", "detalls": str(e)}), 500

    # 4️⃣ Buscar el client que té el `tax-identification-number` igual al DNI
    account_id = None
    for client in clients:
        if client.get("tax-identification-number") == dni:
            main_address = client.get("main-address", {})
            account_id = main_address.get("account-id")
            print("✅ Client trobat:", client)
            break

    if not account_id:
        return jsonify({"error": "No s'ha trobat cap client amb el DNI proporcionat"}), 404

    print("🔹 Account ID del client:", account_id)

    # 5️⃣ Consultem l'API d'incidències per obtenir la llista d'incidències
    try:
        response_incidents = requests.get(INCIDENTS_URL, headers=HEADERS)
        response_incidents.raise_for_status()
        incidents = response_incidents.json()
    except requests.exceptions.RequestException as e:
        print("⚠️ Error en obtenir incidències:", e)
        return jsonify({"error": "Error en obtenir incidències", "detalls": str(e)}), 500

    # 6️⃣ Buscar la incidència que tingui `account-id` igual al trobat
    matching_incident = next((inc for inc in incidents if inc.get("account-id") == account_id), None)

    if not matching_incident:
        return jsonify({"error": "No s'ha trobat cap incidència per aquest account-id", "account_id": account_id}), 404

    # 7️⃣ Extraïm la descripció de la incidència trobada
    description = matching_incident.get("description", "Sense descripció")
    print("📄 Descripció de la incidència:", description)

    # 8️⃣ Retornem la resposta amb la descripció
    return jsonify({"message": "Webhook processat correctament", "description": description}), 200


@app.route('/debug_webhook', methods=['POST'])
def debug_webhook():
    """ Endpoint per depurar les dades rebudes sense processar-les. """
    raw_data = request.get_data(as_text=True)  # Obtenim les dades en cru
    print("\n🔍 RAW JSON REBUT:", raw_data, "\n")
    return jsonify({"message": "Dades rebudes correctament", "json_rebut": raw_data}), 200


if __name__ == '__main__':
    # 🔹 Arrencar el servidor Flask a la porta 5000
    app.run()