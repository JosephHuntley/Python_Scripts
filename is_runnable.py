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
    next_6am = current_time.replace(hour=6, minute=0, second=0, microsecond=0)

    # Check if the current time is greater than 5 PM for the day
    if current_time > next_5pm:
        next_5pm += timedelta(days=1)

    # Check if the current time is greater than 6 AM for the day
    if current_time > next_6am:
        next_6am += timedelta(days=1)

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
    try:
        url = f"{config_data['weather_url']}key={config_data['weather_key']}&q={config_data['zipcode']}&days={days}&aqi={aqi}&alerts={alerts}"
        payload = {}
        headers = {}

        logging.info("Fetching forecast from the weather API...")
        res = requests.request("GET", url, headers=headers, data=payload)
        res.raise_for_status()  # Raise HTTPError for bad responses

        logging.info("Forecast successfully retrieved.")
        return res.text
    except requests.RequestException as e:
        logging.error(f"Error fetching forecast: {e}")
        return None

def get_reason(weather_5pm, weather_6am):
    # Check if 5 PM is runnable
    is_runnable_5pm = weather_5pm['temp_f'] >= 55 and weather_5pm['is_rain'] != 1 and weather_5pm['is_snow'] != 1
    # Generate the reason for 5 PM
    reason_5pm = None if is_runnable_5pm else (
        f"\n\t- Temperature is {weather_5pm['temp_f']}°F, too cold." if weather_5pm['temp_f'] < 55 else "",
        "\n\t- It will rain." if weather_5pm['is_rain'] == 1 else "",
        "\n\t- It will snow." if weather_5pm['is_snow'] == 1 else ""
    )
    # Join the non-empty strings to get the final reason for 5 PM, or set to an empty string if None
    reason_5pm = " ".join(filter(None, reason_5pm)) if reason_5pm is not None else ""

    # Check if 6 AM is runnable
    is_runnable_6am = weather_6am['temp_f'] > 55 and weather_6am['is_rain'] != 1 and weather_6am['is_snow'] != 1
    # Generate the reason for 6 AM
    reason_6am = None if is_runnable_6am else (
        f"\n\t- Temperature is {weather_6am['temp_f']}°F, too cold." if weather_6am['temp_f'] < 55 else "",
        "\n\t- It will rain." if weather_6am['is_rain'] == 1 else "",
        "\n\t- It will snow." if weather_6am['is_snow'] == 1 else ""
    )
    # Join the non-empty strings to get the final reason for 6 AM, or set to an empty string if None
    reason_6am = " ".join(filter(None, reason_6am)) if reason_6am is not None else ""

    return reason_5pm, reason_6am

async def post_to_ha(entity_id, state, friendly_name):
    try:
        url = config_data['HA_URL']
        headers = {
            'Authorization': f'Bearer {config_data["HA_TOKEN"]}',
            'Content-Type': 'application/json',
        }

        payload = {
            'state': state,
            'attributes': {
                'friendly_name': friendly_name,
            },
        }

        logging.info(f'Updating {entity_id}...')
        res = requests.post(
            f'{url}/states/{entity_id}',
            headers=headers,
            json=payload
        )
        res.raise_for_status()  # Raise HTTPError for bad responses

        logging.info(f'{entity_id} updated: {res.status_code}')
    except requests.RequestException as e:
        logging.error(f"Error updating {entity_id}: {e}")

async def main():
    json_data = await get_forecast(2)

    if json_data is not None:
        logging.info("Parsing the JSON data...")
        forecast_data = json.loads(json_data)
        logging.info("JSON data successfully parsed.")

        next_5pm, next_6am = get_next_forecast_times(forecast_data)
        logging.info(f"Next available 5 PM: {next_5pm}, Next available 6 AM: {next_6am}")

        weather_5pm = get_weather_at_time(forecast_data, next_5pm)
        weather_6am = get_weather_at_time(forecast_data, next_6am)

        reason_5pm, reason_6am = get_reason(weather_5pm, weather_6am)

        await post_to_ha('input_boolean.runable_5pm', 'on' if reason_5pm == '' else 'off', 'Runnable 5 PM')
        await post_to_ha('input_text.reason_5pm', reason_5pm, 'Reason 5 PM')

        await post_to_ha('input_boolean.runable_6am', 'on' if reason_6am == '' else 'off', 'Runnable 6 AM')
        await post_to_ha('input_text.reason_6am', reason_6am, 'Reason 6 AM')

if __name__ == "__main__":
    asyncio.run(main())
