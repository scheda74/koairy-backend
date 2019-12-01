from typing import List, Optional
from datetime import datetime
import pandas as pd
import requests
import datetime
import calendar
import json
# from bson.json_util import dumps
from dateutil.relativedelta import relativedelta
from ..tools.predictor.utils.bremicker_boxes import bremicker_boxes
from ..db.mongodb import AsyncIOMotorClient
from ..core.config import (
    database_name, 
    caqi_emission_collection_name,
    raw_emission_collection_name,
    bremicker_collection_name,
    air_hawa_collection_name,
    HAWA_DAWA_URL,
    HAWA_DAWA_API_KEY
)


async def get_hawa_dawa_by_time(conn: AsyncIOMotorClient, start_date='2019-08-01', end_date='2019-11-30', start_hour='07:00', end_hour='10:00', box_id=672):
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    result = []
    async for data in conn[database_name][air_hawa_collection_name].find({}, projection={"_id": False}):
        if data is not None:
            measure_date = datetime.datetime.strptime(data['measure_date'], '%Y-%m-%d').date()
            if start_date <= measure_date <= end_date:
                result.append(data)
        else:
            print('[HAWADAWA] No data in db in loop. Fetching from server')
            response = await fetch_air_traffic(conn)
            if response is not None:
                # return await get_hawa_dawa_by_time(conn, start_date, end_date, start_hour, end_hour)
                result = response
                break
            else:
                print('[HAWA DAWA] error while fetching')
                return None
    # print(result)
    if len(result) == 0:
        print('[HAWADAWA] No data in db. Fetching from server - initial')
        result = await fetch_air_traffic(conn, '2019-01-01')
        # return await get_hawa_dawa_by_time(conn, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), box_id=box_id)
    df = await format_to_df(result, box_id)
    df = df.reset_index()
    mask = (df['time'] > start_date) & (df['time'] <= end_date)
    df = df.loc[mask].set_index('time')
    print(df)
    return df.between_time(start_hour, end_hour)

# async def get_current_hawa_dawa_by_time(conn: AsyncIOMotorClient, start_date='2019-09-01', end_date='2019-09-30', start_hour='07:00', end_hour='10:00', box_id=672):
#     start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
#     end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
#     result = []
#     async for data in conn[database_name][air_hawa_collection_name].find({}, projection={"_id": False}):
#         if data:
#             measure_date = datetime.datetime.strptime(data['measure_date'], '%Y-%m-%d').date()
#             if measure_date >= start_date and measure_date <= end_date:
#                 result.append(data)
#         else:
#             print('[HAWADAWA] No data in db in loop. Fetching from server')
#             response = await fetch_air_traffic(conn)
#             if response:
#                 # return await get_hawa_dawa_by_time(conn, start_date, end_date, start_hour, end_hour)
#                 result = response
#                 break
#             else:
#                 print('[HAWA DAWA] error while fetching')
#                 return None
#
#     if len(result) == 0:
#         print('[HAWADAWA] No data in db. Fetching from server')
#         await fetch_air_traffic(conn, '2019-01-01')
#         # return await get_current_hawa_dawa_by_time(conn, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), box_id=box_id)
#     print('hawa dawa result')
#     print(result)
#     df = await format_to_df(result, box_id)
#     df = df.reset_index()
#     mask = (df['time'] > start_date) & (df['time'] <= end_date)
#     df = df.loc[mask].set_index('time')
#     return df.between_time(start_hour, end_hour)

async def format_to_df(response, box_id=672):
    months = []
    for elem in response:
        data = json.loads(elem['data'])
        for feature in data['features']:
            if (feature['properties']['type'] == 'hawadawa') and feature['properties']['timeValueSeries']:
                # print(bremicker_boxes[box_id]['airSensor'])
                # print(feature['properties']['internal_id'])
                if int(feature['properties']['internal_id']) == int(bremicker_boxes[box_id]['airSensor']):
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
    print("[MONGODB] Saving HawaDawas data of month %s " % str(date))
    raw_doc = {"measure_date": date.strftime('%Y-%m-%d'), "data": json.dumps(data)}
    await conn[database_name][air_hawa_collection_name].insert_one(raw_doc)
    return raw_doc


### NOTE: Fetch data from HawaDawa server
async def fetch_air_traffic(conn: AsyncIOMotorClient, date="2019-01-01"):
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    current_date = datetime.date.today()
    result = []
    while date <= current_date:
        first_day, last_day = get_month_day_range(date)
        data = await fetch_data_by_month_from_hawa_dawa(first_day, last_day)
        data = await insert_air_traffic(conn, date, data)
        result.append(data)
        date = date + relativedelta(months=1)
    return result

async def fetch_latest_air(conn: AsyncIOMotorClient):
    response = await fetch_today_from_hawa_dawa()
    today = datetime.datetime.today()
    today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    print(today)
    result = {}
    for feature in response['features']:
        if (feature['properties']['type'] == 'hawadawa') and feature['properties']['timeValueSeries']:
            df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in feature['properties']['timeValueSeries'].items()]))
            frames = []
            for pollutant in df.columns:
                df_pol = df[pollutant].apply(pd.Series)[['time', 'value']].dropna()
                df_pol['time'] = pd.to_datetime(df_pol['time'])
                df_pol = df_pol.set_index('time')
                df_pol = df_pol.rename(columns={'value': pollutant})
                frames.append(df_pol)
            df = pd.concat(frames, axis=1)
            mask = (df.index >= today)
            df = df.loc[mask]
            df.index = df.index.strftime("%Y-%m-%d %H:%M")
            lng, lat = feature['geometry']['coordinates']
            result[feature['properties']['internal_id']] = {
                # 'id': feature['properties']['internal_id'],
                'location': {'lat': lat, 'lng': lng},
                'values': df.to_dict(orient='index'),
                'aqi': feature['properties']['AQI']
            }
    # print(result)
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
    if response:
        return response.json()
    else:
        return {}

async def fetch_today_from_hawa_dawa():
    today = datetime.date.today().strftime('%Y-%m-%d')
    params = {
        'apikey': HAWA_DAWA_API_KEY,
        'timeseries_startdate': today,
        'show_plausible': False,
        'format': 'geojson',
        'missing_value': -999,
        'crs': 'global'
    }
    response = requests.get(HAWA_DAWA_URL, params=params)
    if response:
        return response.json()
    else:
        return {}

### NOTE: UTILITY FUNCTIONS
def get_month_day_range(date):
    first_day = date.replace(day = 1)
    last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day