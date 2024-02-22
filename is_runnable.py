import json
from datetime import datetime, timedelta
import requests
import logging
import asyncio
from logging_config import load_config, configure_logging

configure_logging()

config_data = load_config()

def get_next_forecast_times(forecast_data):
    current_time = datetime.strptime(forecast_data["location"]["localtime"], "%Y-%m-%d %H:%M")
    next_5pm = current_time.replace(hour=17, minute=0, second=0, microsecond=0)
    next_6am = current_time.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return next_5pm, next_6am

def get_weather_at_time(forecast_data, target_time):
    for forecast_day in forecast_data["forecast"]["forecastday"]:
        for hour_data in forecast_day["hour"]:
            forecast_time = datetime.strptime(hour_data["time"], "%Y-%m-%d %H:%M")
            if forecast_time == target_time:
                return {
                    "temp_f": hour_data["temp_f"],
                    "is_rain": hour_data["will_it_rain"],
                    "is_snow": hour_data["will_it_snow"]
                }

    return None

async def get_forecast(days=1, aqi='no', alerts='no'):
    url = f"{config_data['weather_url']}key={config_data['weather_key']}&q={config_data['zipcode']}&days={days}&aqi={aqi}&alerts={alerts}"
    payload = {}
    headers = {}
    
    # Log that we are fetching the forecast
    logging.info("Fetching forecast from the weather API...")
    
    res = requests.request("GET", url, headers=headers, data=payload)
    
    # Log that we have successfully retrieved the forecast
    logging.info("Forecast successfully retrieved.")
    
    return res.text

def get_reason(weather_5pm, weather_6am):
    # Check if 5 PM is runnable
    is_runnable_5pm = weather_5pm['temp_f'] >= 55 and weather_5pm['is_rain'] != 1 and weather_5pm['is_snow'] != 1
    # Generate the reason for 5 PM
    reason_5pm = None if is_runnable_5pm else (
        f"Temperature is {weather_5pm['temp_f']}°F, too cold." if weather_5pm['temp_f'] < 55 else "",
        "\nIt will rain." if weather_5pm['is_rain'] == 1 else "",
        "\nIt will snow." if weather_5pm['is_snow'] == 1 else ""
    )
    # Join the non-empty strings to get the final reason for 5 PM, or set to an empty string if None
    reason_5pm = " ".join(filter(None, reason_5pm)) if reason_5pm is not None else ""

    # Check if 6 AM is runnable
    is_runnable_6am = weather_6am['temp_f'] > 55 and weather_6am['is_rain'] != 1 and weather_6am['is_snow'] != 1
    # Generate the reason for 6 AM
    reason_6am = None if is_runnable_6am else (
        f"Temperature is {weather_6am['temp_f']}°F, too cold." if weather_6am['temp_f'] < 55 else "",
        "\nIt will rain." if weather_6am['is_rain'] == 1 else "",
        "\nIt will snow." if weather_6am['is_snow'] == 1 else ""
    )
    # Join the non-empty strings to get the final reason for 6 AM, or set to an empty string if None
    reason_6am = " ".join(filter(None, reason_6am)) if reason_6am is not None else ""

    return reason_5pm, reason_6am

async def post_to_ha(reason_5pm, reason_6am):
    url = config_data['HA_URL']
    
    entity_ids = [
        'input_boolean.runable_5pm',
        'input_boolean.runable_6am',
        'input_text.reason_5pm',
        'input_text.reason_6am',
    ]

    headers = {
        'Authorization': f'Bearer {config_data["HA_TOKEN"]}',
        'Content-Type': 'application/json',
    }

    for entity_id, reason in zip(entity_ids, [reason_5pm, reason_6am]):
        logging.info(f'{entity_id}, {reason}')
        # Determine if it is runnable (reason is None)
        is_runnable = reason == ''

        # Prepare payload for updating entities
        payload = {
            'state': 'on' if is_runnable else 'off',
            'attributes': {
                'friendly_name': entity_id.split('.')[-1].replace('_', ' ').title(),
            },
        }

        # Update state
        res = requests.post(
            f'{url}/states/{entity_id}',
            headers=headers,
            json=payload
        )
        # logging.info(f'{entity_id}: {res.text}')

        # Update reason if it exists
        reason = "You can run!" if reason == '' else reason

        payload_reason = {
            'state': reason,
        }
        res = requests.post(
            f'{url}/states/{entity_id.replace("boolean.runable", "text.reason")}',
            headers=headers,
            json=payload_reason
        )
        logging.info(f'{entity_id.replace("runable", "reason")}: {res.text}')
    


async def main():
    # Your JSON data
    json_data = await get_forecast(2)
    
    # Log that we are parsing the JSON data
    logging.info("Parsing the JSON data...")
    
    # Parse the JSON data
    forecast_data = json.loads(json_data)
    
    # Log that we have successfully parsed the JSON data
    logging.info("JSON data successfully parsed.")
    
    # Get the next available 5 PM and 6 AM
    next_5pm, next_6am = get_next_forecast_times(forecast_data)
    
    # Log the next forecast times
    logging.info(f"Next available 5 PM: {next_5pm}, Next available 6 AM: {next_6am}")

    # Get weather conditions at the next available 5 PM and 6 AM
    weather_5pm = get_weather_at_time(forecast_data, next_5pm)
    weather_6am = get_weather_at_time(forecast_data, next_6am)

    reason_5pm, reason_6am = get_reason(weather_5pm, weather_6am)    

    await post_to_ha(reason_5pm, reason_6am)

    # Print the temperatures and weather conditions with reasons
    # logging.info(f"Is Runnable at 5 PM: {is_runnable_5pm or 'Reason: ' + ('Temperature <= 55' if weather_5pm['temp_f'] <= 55 else 'Rain or Snow')}. {reason_5pm}")

    # logging.info(f"Is Runnable at 6 AM: {is_runnable_6am or 'Reason: ' + ('Temperature <= 55' if weather_6am['temp_f'] <= 55 else 'Rain or Snow')}. {reason_6am}")

if __name__ == "__main__":
    asyncio.run(main())
