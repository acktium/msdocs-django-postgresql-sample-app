import requests
import pandas as pd
from datetime import datetime



class Weather:
    def __init__(self, api_key):
        self._api_key = api_key

    def fetch_weather(self, lat, lon, timestamp):
        """Fetch weather data for a specific timestamp and location using OpenWeather API."""
        url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={timestamp}&appid={self._api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch weather data: {response.status_code} {response.text}")
        
    def extract_weather_data(self, api_response):
        """Extract wind speed, wind gust, and wind direction from the API response."""
        data = api_response['data'][0]
        return {
            'Timestamp': datetime.utcfromtimestamp(data['dt']),
            'Wind Speed': data['wind_speed'],
            'Wind Gust': data.get('wind_gust', 0),  # Some responses may not have wind gust
            'Wind Direction': data['wind_deg']
        }
    
    def get_weather_data(self, lat, lon, start_time, end_time, interval):
        """Fetch weather data for a range of timestamps and locations.
        interval in minutes
        """
        start_timestamp = int(start_time.timestamp())
        # + intervall
        end_timestamp = int(end_time.timestamp()) + interval * 60
        current_timestamp = start_timestamp
        weather_data = []
        while current_timestamp <= end_timestamp:
            api_response = self.fetch_weather(lat, lon, current_timestamp)
            weather_data.append(self.extract_weather_data(api_response))
            current_timestamp += interval * 60
        weather_data = pd.DataFrame(weather_data)
        weather_data['Timestamp'] = pd.to_datetime(weather_data['Timestamp']).dt.tz_localize('UTC')

        return weather_data
