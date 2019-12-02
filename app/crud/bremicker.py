import pandas as pd
import requests
import datetime
from json import JSONDecodeError

from ..db.mongodb import AsyncIOMotorClient

from ..core.config import (
    database_name,
    BREMICKER_API_KEY,
    BREMICKER_URL,
    bremicker_collection_name
)


async def get_bremicker(conn: AsyncIOMotorClient, start_date='2019-09-01', end_date='2019-09-30'):
    data = await conn[database_name][bremicker_collection_name].find_one({}, projection={"_id": False})
    if not data:
        print('[BREMICKER] No data in db. Fetching from server')
        await fetch_bremicker(conn, start_date, end_date)
        return await conn[database_name][bremicker_collection_name].find_one({}, projection={"_id": False})
        # if response:
        #     # return await get_bremicker(conn, start_date, end_date)
        # else:
        #     raise Exception('Error in fetching bremicker data')
    return data


async def get_bremicker_by_time(conn: AsyncIOMotorClient, box_id, start_date='2019-08-01', end_date='2019-11-01', start_hour='07:00', end_hour='10:00'):
    box_id = int(box_id)
    bremicker = await get_bremicker(conn, start_date, end_date)
    if bremicker['data']:
        df_traffic = pd.DataFrame(pd.read_json(bremicker['data']))
    elif bremicker is not None:
        df_traffic = pd.DataFrame(pd.read_json(bremicker))
    else:
        return None
    df_traffic.index.name = 'time'
    df = df_traffic.reset_index()[['time', box_id]]
    mask = (df['time'] >= start_date) & (df['time'] <= end_date)
    df = df.loc[mask].set_index('time')
    return df.between_time(start_hour, end_hour)


async def get_current_bremicker_by_time(conn: AsyncIOMotorClient, start_date=None, end_date=None, start_hour=None, end_hour=None):
    try:
        print('[BREMICKER] Start fetching bremicker data...')
        bremicker = await fetch_current_bremicker(conn, start_date, end_date)
    except Exception as e:
        raise Exception('[BREMICKER] fetching not successful! %s' % str(e))
    if bremicker is not None:
        df_traffic = pd.DataFrame(pd.read_json(bremicker))
        df_traffic.index.name = 'time'
        print(df_traffic)
        if start_hour is None or end_hour is None:
            return df_traffic
        else:
            return df_traffic.between_time(start_hour, end_hour)
    else:
        return None


async def get_latest_bremicker_by_box_id(conn: AsyncIOMotorClient, box_id=672):
    df_traffic = await get_current_bremicker_by_time(conn)
    if df_traffic is not None:
        print(df_traffic)
        df_traffic = df_traffic[int(box_id)]
        # return df_traffic.iloc[[-1]]
        return df_traffic
    else:
        return None


### NOTE: Fetch data from bremicker
async def fetch_bremicker(conn: AsyncIOMotorClient, start_date='2019-06-20', end_date=None):
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date is not None:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.date.today()
    print(start_date)
    print(end_date)
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
        raise Exception('Error while decoding bremicker response...')
    except Exception as e:
        raise Exception('Error while fetching bremicker: %s ' % str(e))
    else:
        return response


async def fetch_current_bremicker(conn: AsyncIOMotorClient, start_date=None, end_date=None):
    if start_date is not None:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.date.today()

    if end_date is not None:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.date.today()
    # print(start_date)
    # print(end_date)
    params = {
        'key': BREMICKER_API_KEY,
        'from': start_date,
        'to': end_date,
    }
    try:
        response = requests.get(BREMICKER_URL, params=params)
        response = response.json()
        # print(response)
        response = await format_bremicker(response)
        # await insert_bremicker(conn, start_date, response)
        # print(response)
    except JSONDecodeError as error:
        raise Exception('[BREMICKER] Error in json decoding: %s' % error)
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
    print(df)
    return df


async def insert_bremicker(conn: AsyncIOMotorClient, date, data: dict):
    print("[MONGODB] Saving Bremicker data")
    raw_doc = {}
    raw_doc["measure_date"] = date.strftime('%Y-%m-%d')
    raw_doc["data"] = data
    await conn[database_name][bremicker_collection_name].insert_one(raw_doc)
    print("[MONGODB] Bremicker data successfully saved!")