import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs
from geopy.distance import geodesic
import logging
from .weather import Weather


logger = logging.getLogger(__name__)

class ProcessSessionData:
    def __init__(self, data = None, openweathermap_api_key = None):
        self.data = data
        self.openweathermap_api_key = openweathermap_api_key

    def read_tcx(self, tcx_file_path):
        # extract the time, latitude, longitude, altitude, and heart rate data

        # Read and parse the TCX file
        with open(tcx_file_path, 'r') as file:
            soup = bs(file, 'xml')

        # Create lists to store the data
        times = []
        latitudes = []
        longitudes = []
        altitudes = []
        heart_rates = []

        # Extract data from each trackpoint
        for trackpoint in soup.find_all('Trackpoint'):
            times.append(trackpoint.Time.text if trackpoint.Time else None)
            latitudes.append(trackpoint.Position.LatitudeDegrees.text if trackpoint.Position and trackpoint.Position.LatitudeDegrees else None)
            longitudes.append(trackpoint.Position.LongitudeDegrees.text if trackpoint.Position and trackpoint.Position.LongitudeDegrees else None)
            altitudes.append(trackpoint.AltitudeMeters.text if trackpoint.AltitudeMeters else None)
            heart_rates.append(trackpoint.HeartRateBpm.Value.text if trackpoint.HeartRateBpm and trackpoint.HeartRateBpm.Value else None)

        # Create a DataFrame
        data = {
            'Time': times,
            'Latitude': latitudes,
            'Longitude': longitudes,
            'Altitude': altitudes,
            'Heart Rate': heart_rates
        }
        data = pd.DataFrame(data)

        # convert the data to the correct data types
        data['Time'] = pd.to_datetime(data['Time'])
        data['Latitude'] = data['Latitude'].astype(float)
        data['Longitude'] = data['Longitude'].astype(float)
        data['Altitude'] = data['Altitude'].astype(float)
        data['Heart Rate'] = data['Heart Rate'].astype(float)

        # drop any rows with missing data
        data = data.dropna()

        data.index = data['Time']

        self.data = data

        return data
    
    def calculate_derivables(self):
        # calculate the time deltas
        self.data['Time Delta'] = self.data['Time'].diff().dt.total_seconds()

        # calculate the distance deltas
        self.data['Distance Delta'] = 0.0
        
        self.calc_distance()

        # calculate the speed
        self.data['Speed'] = self.data['Distance Delta'] / self.data['Time Delta'] 

        # calculate the acceleration
        self.data['Acceleration'] = self.data['Speed'].diff() / self.data['Time Delta']

        # calculate the direction, 0 for south, 90 for west, 180 for north, 270 for east
        self.data['Direction'] = 0
        # Shift the lat and lon columns to align for pairwise calculation
        lat_next = self.data['Latitude'].shift(-1)
        lon_next = self.data['Longitude'].shift(-1)

        # Calculate the bearing using vectorized operations
        self.data['Direction'] = np.vectorize(self.calculate_bearing)(self.data['Latitude'], self.data['Longitude'], lat_next, lon_next)

        return self.data
    
    @staticmethod
    def calculate_bearing(lat1, lon1, lat2, lon2):
        # Function to calculate the bearing
        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])

        dLon = lon2 - lon1
        x = np.sin(dLon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dLon)
        initial_bearing = np.arctan2(x, y)
        initial_bearing = np.degrees(initial_bearing)
        bearing = (initial_bearing + 360) % 360

        return bearing
    
    def filter_outliers(self):
        #Points that are beyond 1.5 times the IQR are beyond the expected range of variation of the data. 

        # Calculate the interquartile range
        Q1 = self.data['Heart Rate'].quantile(0.25)
        Q3 = self.data['Heart Rate'].quantile(0.75)
        IQR = Q3 - Q1

        # Filter out the outliers
        filter = (self.data['Heart Rate'] >= Q1 - 1.5 * IQR) & (self.data['Heart Rate'] <= Q3 + 1.5 * IQR)
        self.data = self.data[filter]

        logger.info(f'Filtered out {len(self.data) - len(filter)} outliers for heart rate')

        # Calculate the interquartile range
        Q1 = self.data['Speed'].quantile(0.25)
        Q3 = self.data['Speed'].quantile(0.75)
        IQR = Q3 - Q1

        # Filter out the outliers
        filter = (self.data['Speed'] >= Q1 - 1.5 * IQR) & (self.data['Speed'] <= Q3 + 1.5 * IQR)
        self.data = self.data[filter]

        logger.info(f'Filtered out {len(self.data) - len(filter)} outliers for speed')

        return self.data
    
    def append_weather(self):
        # get the start and end times of the session
        start_time = self.data.index.min()
        end_time = self.data.index.max()

        # get the latitude and longitude of the session
        lat = self.data['Latitude'].mean()
        lon = self.data['Longitude'].mean()

        # get the weather data
        weather = Weather(self.openweathermap_api_key)
        weather_data = weather.get_weather_data(lat, lon, start_time, end_time, 10)

        # merge the weather data with the session data: integrate the weather timepoints, interpolate missing values, drop the weather timepoints
        # Initialize columns for weather data
        self.data['Wind Speed'] = np.nan
        self.data['Wind Gust'] = np.nan
        self.data['Wind Direction'] = np.nan

        # Merge weather data with session data based on the closest timestamps
        closest_indices = self.data.index.get_indexer(weather_data['Timestamp'], method='nearest')
        self.data.loc[closest_indices, ['Wind Speed', 'Wind Gust', 'Wind Direction']] = weather_data[['Wind Speed', 'Wind Gust', 'Wind Direction']].values


        # Remove timezone information
        self.data.index = self.data.index.tz_localize(None)

        # Perform time-based interpolation
        self.data = self.data.interpolate(method='time')

        # Reapply the timezone if needed
        self.data.index = self.data.index.tz_localize('UTC')
    

        return self.data
    
    def calculate_relative_surf_direction(self):
        # calculate the relative surf direction
        self.data['Relative Surf Direction'] = self.data['Direction'] - self.data['Wind Direction']
        self.data['Relative Surf Direction'] = self.data['Relative Surf Direction'] % 360

        return self.data

    def smooth_data(self, time_delta=10):
        # time index

        self.data = self.data.resample(f'{time_delta}S').mean()
        # smooth the data
        pass

    @staticmethod
    def haversine_vectorized(lat1, lon1, lat2, lon2):
        R = 6371000  # Radius of Earth in meters
        phi1 = np.radians(lat1)
        phi2 = np.radians(lat2)
        delta_phi = np.radians(lat2 - lat1)
        delta_lambda = np.radians(lon2 - lon1)
        
        a = np.sin(delta_phi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    def calc_distance(self):
        # Shift the latitude and longitude columns to calculate the distance between consecutive points
        self.data['Latitude_shift'] = self.data['Latitude'].shift(-1)
        self.data['Longitude_shift'] = self.data['Longitude'].shift(-1)

        # Calculate distances
        self.data['Distance Delta'] = self.haversine_vectorized(self.data['Latitude'], self.data['Longitude'], self.data['Latitude_shift'], self.data['Longitude_shift'])

        # Drop the last row which contains NaN after the shift
        self.data = self.data[:-1]

        # Drop the temporary shifted columns
        self.data.drop(columns=['Latitude_shift', 'Longitude_shift'], inplace=True)


        return self.data