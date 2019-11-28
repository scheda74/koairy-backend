from typing import List, Optional
from datetime import datetime
import pandas as pd
import requests
import datetime
import calendar
import json
# from bson.json_util import dumps
from dateutil.relativedelta import relativedelta

from app.db.mongodb import AsyncIOMotorClient
from app.core.config import (
    database_name, 
    caqi_emission_collection_name,
    raw_emission_collection_name,
    bremicker_collection_name,
    air_hawa_collection_name,
    HAWA_DAWA_URL,
    HAWA_DAWA_API_KEY
)

# async def get_all_hawa_dawa(conn: AsyncIOMotorClient):
#     result = []
#     async for data in conn[database_name][air_hawa_collection_name].find({}, projection={"_id": False}):
#         if data:
#             result.append(data)
#         else:
#             break    
    
#     if len(result) == 0: 
#         return await fetch_air_traffic(conn, '2019-01-01')
#     return await format_to_df(result)

async def get_hawa_dawa_by_time(conn: AsyncIOMotorClient, start_date='2019-09-01', end_date='2019-09-30', start_hour='07:00', end_hour='10:00'):
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    result = []
    async for data in conn[database_name][air_hawa_collection_name].find({}, projection={"_id": False}):
        if data:
            measure_date = datetime.datetime.strptime(data['measure_date'], '%Y-%m-%d').date()
            if measure_date >= start_date and measure_date <= end_date:
                result.append(data)
        else:
            response = await fetch_air_traffic(conn)
            if response:
                return await get_hawa_dawa_by_time(conn, start_date, end_date, start_hour, end_hour)
            else:
                print('[HAWA DAWA] error while fetching')
                return None

    if len(result) == 0: 
        await fetch_air_traffic(conn, '2019-01-01')
        return await get_hawa_dawa_by_time(conn, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    df = await format_to_df(result)
    df = df.reset_index()
    mask = (df['time'] > start_date) & (df['time'] <= end_date)
    df = df.loc[mask].set_index('time')
    return df.between_time(start_hour, end_hour)



async def format_to_df(response):
    months = []
    for elem in response:
        data = json.loads(elem['data'])
        for feature in data['features']:
            if (feature['properties']['type'] == 'hawadawa') and feature['properties']['timeValueSeries']:
                df = pd.DataFrame(dict([ (k, pd.Series(v)) for k, v in feature['properties']['timeValueSeries'].items() ]))
                frames = []
                for pollutant in df.columns:
                    df_pol = df[pollutant].apply(pd.Series)[['time', 'value']].dropna()
                    df_pol['time'] = pd.to_datetime(df_pol['time'])
                    df_pol = df_pol.set_index('time')
                    df_pol = df_pol.rename(columns={'value': pollutant})
                    frames.append(df_pol)
                months.append( pd.concat(frames, axis=1).dropna() )
    result = pd.concat(months)
    # print(result)
    return result

async def insert_air_traffic(conn: AsyncIOMotorClient, date, data: dict):
    print("[MONGODB] Saving HawaDawas data of {date}")
    raw_doc = {}
    raw_doc["measure_date"] = date.strftime('%Y-%m-%d')
    raw_doc["data"] = json.dumps(data)
    await conn[database_name][air_hawa_collection_name].insert_one(raw_doc)

### NOTE: Fetch data from HawaDawa server
async def fetch_air_traffic(conn: AsyncIOMotorClient, date="2019-01-01"):
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    current_date = datetime.date.today()
    result = []
    while date < current_date:
        first_day, last_day = get_month_day_range(date)
        data = await fetch_data_by_month_from_hawa_dawa(first_day, last_day)
        await insert_air_traffic(conn, first_day, data)
        result.append(data)
        date = date + relativedelta(months=1)
    return result

async def fetch_data_by_month_from_hawa_dawa(start_date, end_date):
    params = {
        'apikey': HAWA_DAWA_API_KEY,
        'timeseries_startdate': start_date, 
        'timeseries_enddate': end_date, 
        'show_plausible': False,
        'format': 'geojson',
        'missing_value': -999,
        'crs': 'global'
    }
    response = requests.get(HAWA_DAWA_URL, params=params)
    return response.json()


### NOTE: UTILITY FUNCTIONS
def get_month_day_range(date):
    first_day = date.replace(day = 1)
    last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day