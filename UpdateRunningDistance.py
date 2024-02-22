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
running_distance = 0
try:
    res = requests.request("GET", config_data['s_url'], headers=headers, data=payload)
    res.raise_for_status()  # Raise an exception for HTTP errors
    logging.info(f"Strava API HTTP Status Code: {res.status_code}")

    running_distance = round(json.loads(res.text)['ytd_run_totals']['distance'] / 1609.34, 2)
    logging.info(f"Running Distance: {running_distance}")
except Exception as e:
    logging.error(f"An error has occurred with the Strava api: {e}")
    
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
    if(running_distance == 0):
        raise ValueError("Running distance is zero")

    # Make the POST request to the Home Assistant API with the updated running distance value
    data = json.dumps({"state": running_distance})
    response = requests.post(api_endpoint, headers=headers, data=data)
    response.raise_for_status()  # Raise an exception for HTTP errors
    logging.info(f"HA API HTTP Status Code: {response.status_code}")
except requests.exceptions.RequestException as e:
    logging.error(f"Error updating running distance status on HA server: {e}")
except ValueError as e:
    logging.error(f"Error: {e}")
