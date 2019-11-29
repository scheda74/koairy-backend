from typing import List, Optional
from datetime import datetime
import pandas as pd
import requests
import datetime
import calendar
import json
from json import JSONDecodeError
from bson.json_util import dumps
from dateutil.relativedelta import relativedelta

from app.db.mongodb import AsyncIOMotorClient

from app.core.config import (
    database_name,
    BREMICKER_API_KEY,
    BREMICKER_URL,
    bremicker_collection_name
)

async def get_bremicker_by_time(conn: AsyncIOMotorClient, boxID, start_date='2019-08-01', end_date='2019-11-01', start_hour='07:00', end_hour='10:00'):
    boxID = int(boxID)
    bremicker = await get_bremicker(conn, start_date, end_date)
    if bremicker['data']:
        df_traffic = pd.DataFrame(pd.read_json(bremicker['data']))
    else:
        df_traffic = pd.DataFrame(pd.read_json(bremicker))
    df_traffic.index.name = 'time'
    df = df_traffic.reset_index()[['time', boxID]]
    mask = (df['time'] > start_date) & (df['time'] <= end_date)
    df = df.loc[mask].set_index('time')
    return df.between_time(start_hour, end_hour)


async def get_bremicker(conn: AsyncIOMotorClient, start_date='2019-09-01', end_date='2019-09-30'):
    data = await conn[database_name][bremicker_collection_name].find_one({}, projection={"_id": False})
    if not data:
        print('[BREMICKER] No data in db. Fetching from server')
        response = await fetch_bremicker(conn, start_date, end_date)
        if response:
            return await get_bremicker(conn, start_date, end_date)
        else:
            return None
    return data

async def get_current_bremicker_by_time(conn: AsyncIOMotorClient, start_date=None, end_date=None, start_hour='07:00', end_hour='10:00'):
    try:
        bremicker = await fetch_current_bremicker(conn, start_date, end_date)
    except Exception as e:
        print('[BREMICKER] fetching not successful! %s' % str(e))
    df_traffic = pd.DataFrame(pd.read_json(bremicker))
    df_traffic.index.name = 'time'
    return df_traffic.between_time(start_hour, end_hour)

### NOTE: Fetch data from bremicker
async def fetch_bremicker(conn: AsyncIOMotorClient, start_date='2019-06-20', end_date=None):
    print('[MongoDB] No bremicker data found. Fetching from server...')
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.date.today()
    params = {
        'key': BREMICKER_API_KEY,
        'from': start_date, 
        'to': end_date, 
    }
    try:
        response = requests.get(BREMICKER_URL, params=params)
        response = response.json()
        response = await format_bremicker(response)
        await insert_bremicker(conn, start_date, response)
        
    except JSONDecodeError as error:
        print('error in json decoding: %s' % error)
        return None
    else:
        return response

async def fetch_current_bremicker(conn: AsyncIOMotorClient, start_date=None, end_date=None):
    print('[MongoDB] No bremicker data found. Fetching from server...')
    if start_date:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.date.today()

    if end_date:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.date.today()

    params = {
        'key': BREMICKER_API_KEY,
        'from': start_date,
        'to': end_date,
    }
    try:
        response = requests.get(BREMICKER_URL, params=params)
        response = response.json()
        print('response')
        # print(response)
        response = await format_bremicker(response)
        # await insert_bremicker(conn, start_date, response)
        print(response)
    except JSONDecodeError as error:
        print('error in json decoding: %s' % error)
    else:
        return response

async def format_bremicker(data):
    df = pd.DataFrame(data)
    df['time'] = df[['date', 'time']].apply(lambda x: pd.to_datetime(' '.join(x)), axis=1)
    df = df[['time', 'boxID', 'averageVelocity', 'entryVelocity']]
    df = df.groupby(['boxID', pd.Grouper(key='time', freq='H')]).size()
    df = df.reset_index().rename(columns={0: 'veh'})
    df['time'] = df['time'].astype(str)
    df = df.groupby('boxID')[['time', 'veh']].apply(lambda x: dict(x.values)).to_json()
    # times = df['time']
    # df = df.groupby(['boxID', times.dt.date, times.dt.hour])[['averageVelocity', 'entryVelocity']].mean()
    # [['averageVelocity', 'entryVelocity']].mean()
    # df['veh'] = df.resample('H').transform('count')
    # df = df.groupby(by=df['time'].dt.hour)[['averageVelocity', 'entryVelocity']].mean()
    # df.groupby(['boxID'])[['averageVelocity', 'entryVelocity']]
    # df = df[['date', 'time']]
    print(df)
    return df
    # for measure in data:
    #     time = pd.to_datetime(measure['date'] + measure['time'])

async def insert_bremicker(conn: AsyncIOMotorClient, date, data: dict):
    print("[MONGODB] Saving Bremicker data")
    raw_doc = {}
    raw_doc["measure_date"] = date.strftime('%Y-%m-%d')
    raw_doc["data"] = data
    await conn[database_name][bremicker_collection_name].insert_one(raw_doc)
    print("[MONGODB] Bremicker data successfully saved!")