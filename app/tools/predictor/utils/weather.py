
import datetime
import pandas as pd
from app.core.config import (
    WEATHER_BASEDIR,
    WEATHER_PRESSURE,
    WEATHER_TEMP_HUMID, 
    WEATHER_WIND,
    AIR_BASEDIR,
    PLOT_BASEDIR
)

async def fetch_weather_data(start_date='2019-01-01', end_date='2019-10-28', start_hour='0:00', end_hour='23:00'):
    # NOTE: Fetch weather data and format timestamp
    df_temp_humid = get_temp_humid()
    df_temp = format_weather_by_key(
        df=df_temp_humid,
        key='TEMP',
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour
    )
    # save_df_to_plot(df_temp, 'temp_02-06_morning')

    df_humidity = format_weather_by_key(
        df=df_temp_humid,
        key='HUMIDITY',
        start_date=start_date,
        end_date=end_date,
        start_hour=start_hour,
        end_hour=end_hour
    )
    # save_df_to_plot(df_humidity, 'humidity_02-06_morning')

    df_pressure = get_pressure()
    df_pressure_nn = format_weather_by_key(
        df=df_pressure, 
        key='PRESSURE_NN', 
        start_date=start_date, 
        end_date=end_date, 
        start_hour=start_hour, 
        end_hour=end_hour
    )
    # save_df_to_plot(df_pressure_nn, 'pressure-nn_02-06_morning')

    df_wind = get_wind()
    df_wind_speed = format_weather_by_key(
        df=df_wind, 
        key='WIND_SPEED', 
        start_date=start_date, 
        end_date=end_date, 
        start_hour=start_hour, 
        end_hour=end_hour
    )

    df_wind_dir = format_weather_by_key(
        df=df_wind, 
        key='WIND_DIR', 
        start_date=start_date, 
        end_date=end_date, 
        start_hour=start_hour, 
        end_hour=end_hour
    )
    # print(df_wind_dir)
    # df_wind['MESS_DATUM'] = pd.to_datetime(df_wind['MESS_DATUM'])
    # print(df_wind)
    # save_df_to_plot(df_wind_speed, 'pressure-nn_02-06_morning')
    return pd.concat([frame for frame in [df_temp, df_humidity, df_pressure_nn, df_wind_speed, df_wind_dir] if not frame.empty], axis=1)



def get_temp_humid():
    df = pd.read_csv(WEATHER_TEMP_HUMID, delimiter=';')
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"TT_TU": "TEMP", "RF_TU": "HUMIDITY"})
    return df[['MESS_DATUM', 'TEMP', 'HUMIDITY']]
    # humidty, temperature = np.loadtxt(WEATHER_TEMP_HUMID, delimiter=';', usecols=(3, 4), skiprows=1, unpack=True)

def get_pressure():
    df = pd.read_csv(WEATHER_PRESSURE, delimiter=';')
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"P": "PRESSURE_NN", "P0": "PRESSURE_STATION"})
    return df[['MESS_DATUM', 'PRESSURE_NN', 'PRESSURE_STATION']]
    # return 0

def get_wind():
    df = pd.read_csv(WEATHER_WIND, delimiter=';')
    df.columns = df.columns.str.strip()
    df = df.rename(columns={"F": "WIND_SPEED", "D": "WIND_DIR"})
    return df[['MESS_DATUM', 'WIND_SPEED', 'WIND_DIR']]

def format_weather_by_key(df, key, start_date, end_date, start_hour, end_hour):
    df = df[['MESS_DATUM', key]]
    df['MESS_DATUM'] = df['MESS_DATUM'].apply(lambda x: datetime.datetime.strptime(str(x), '%Y%m%d%H'))
    # return df.set_index('MESS_DATUM')
    mask = (df['MESS_DATUM'] > start_date) & (df['MESS_DATUM'] <= end_date)
    df = df.loc[mask].set_index('MESS_DATUM')
    return df.between_time(start_hour, end_hour)