import requests
import json
import logging
from logging_config import load_config, configure_logging

configure_logging()
config_data = load_config()

# Fetch running and biking distance from Strava API
payload = {}
headers = {
    'Authorization': f"Bearer {config_data['s_api_key']}"
}

running_distance = 0
biking_distance = 0

try:
    res = requests.request("GET", config_data['s_url'], headers=headers, data=payload)
    res.raise_for_status()  # Raise an exception for HTTP errors
    logging.info(f"Strava API HTTP Status Code: {res.status_code}")

    data = json.loads(res.text)

    running_distance = round(data['ytd_run_totals']['distance'] / 1609.34, 2)
    logging.info(f"Running Distance: {running_distance}")

    biking_distance = round(data['ytd_ride_totals']['distance'] / 1609.34, 2)
    logging.info(f"Biking Distance: {biking_distance}")

except Exception as e:
    logging.error(f"An error has occurred with the Strava API: {e}")

# Update running distance in Home Assistant
headers = {
    'Authorization': f'Bearer {config_data["HA_TOKEN"]}',
    'Content-Type': 'application/json',
}

# Specify the entity_id for the input_number entities
entity_id_running = 'input_number.ytd_running_distance'
entity_id_biking = 'input_number.ytd_biking_distance'

# Build the API endpoint for updating the state of the entities
api_endpoint_running = f'{config_data["HA_URL"]}/states/{entity_id_running}'
api_endpoint_biking = f'{config_data["HA_URL"]}/states/{entity_id_biking}'

try:
    if running_distance == 0:
        raise ValueError("Running distance is zero")
    if biking_distance == 0:
        raise ValueError("Biking distance is zero")

    # Make the POST requests to the Home Assistant API with the updated distance values
    data_running = json.dumps({"state": running_distance})
    data_biking = json.dumps({"state": biking_distance})

    response_running = requests.post(api_endpoint_running, headers=headers, data=data_running)
    response_biking = requests.post(api_endpoint_biking, headers=headers, data=data_biking)

    response_running.raise_for_status()
    response_biking.raise_for_status()

    logging.info(f"HA API HTTP Status Code - Running: {response_running.status_code}")
    logging.info(f"HA API HTTP Status Code - Biking: {response_biking.status_code}")

except requests.exceptions.RequestException as e:
    logging.error(f"Error updating distance status on HA server: {e}")
except ValueError as e:
    logging.error(f"Error: {e}")