import requests
import json
import logging
from logging_config import load_config, configure_logging

configure_logging()
config_data = load_config()

# Fetch running distance from Strava API
payload = {}
headers = {
    'Authorization': f"Bearer {config_data['s_api_key']}"
}

res = requests.request("GET", config_data['s_url'], headers=headers, data=payload)

running_distance = round(json.loads(res.text)['ytd_run_totals']['distance'] / 1609.34, 2)
logging.info(running_distance)

# Update running distance in Home Assistant
headers = {
    'Authorization': f'Bearer {config_data["HA_TOKEN"]}',
    'Content-Type': 'application/json',
}

# Specify the entity_id for the input_select.armed_mode
entity_id = 'input_number.ytd_running_distance'

# Build the API endpoint for updating the state of the entity
api_endpoint = f'{config_data["HA_URL"]}/states/{entity_id}'

try:
    # Make the POST request to the Home Assistant API with the updated running distance value
    data = json.dumps({"state": running_distance})
    response = requests.post(api_endpoint, headers=headers, data=data)
    response.raise_for_status()  # Raise an exception for HTTP errors
    logging.info(f"HTTP Status Code: {response.status_code}")
except requests.exceptions.RequestException as e:
    logging.error(f"Error updating running distance status: {e}")
