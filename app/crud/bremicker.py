import pandas as pd
import requests
import datetime
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from datetime import timedelta
from json import JSONDecodeError
from ..db.mongodb import AsyncIOMotorClient
from ..core.config import (
    database_name,
    BREMICKER_API_KEY,
    BREMICKER_URL,
    bremicker_collection_name
)


async def get_bremicker(conn: AsyncIOMotorClient, start_date=None, end_date=None, grouper_freq='10Min'):
    if start_date is not None:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.datetime.today().date()
    start_date = datetime.datetime.combine(start_date, datetime.time.min)

    if end_date is not None:
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.datetime.today().date()
    end_date = datetime.datetime.combine(end_date, datetime.time.min)
    print(start_date)
    print(end_date)
    try:
        docs = await conn[database_name][bremicker_collection_name].count_documents({"$and": [{"measure_date": {"$gte": start_date}}, {"measure_date": {"$lte": end_date}}]})
        if docs < 2:
            print('Fetching bremicker data from %s to %s from server' % (start_date, end_date))
            await fetch_bremicker(conn, start_date, end_date)
        result = []
        async for document in conn[database_name][bremicker_collection_name].find({"$and": [{"measure_date": {"$gte": start_date}}, {"measure_date": {"$lte": end_date}}]}):
            if document is None or len(document['data']) == 0:
                await fetch_bremicker(conn, document['measure_date'], document['measure_date'])
                continue
            try:
                print('fetching data from %s' % document['measure_date'].strftime('%Y-%m-%d'))
                df = pd.DataFrame.from_dict(document['data'])
                df['date'] = document['measure_date'].strftime('%Y-%m-%d')
                df['time'] = df[['date', 'time']].apply(lambda x: pd.to_datetime(' '.join(x)), axis=1)
                df = df.groupby([pd.Grouper(key='time', freq=grouper_freq), 'boxID']).size().reset_index()
                df['time'] = df['time'].astype(str)
                df = df.set_index('time').rename(columns={0: 'numberOfVehicles'})
                df = df.reset_index()
                df = df.pivot(index='time', values='numberOfVehicles', columns='boxID').reset_index().rename_axis(None, axis=1)
                df = df.set_index('time')
                result.append(df)
            except Exception as e:
                print(str(e))
                raise Exception('[BREMICKER] Error in fetching from db: %s' % str(e))
        df = pd.concat(result).fillna(0)
        # print(df)
        return df
    except Exception as e:
        await drop_bremicker(conn)
        raise Exception('[BREMICKER] Error in fetching from db: %s' % str(e))


async def drop_bremicker(conn):
    try:
        await conn[database_name][bremicker_collection_name].drop()
    except Exception as e:
        raise Exception("[MONGODB] Error while deleting collections: %s" % str(e))
    else:
        print("[MONGODB] Bremicker collection successfully dropped!")


async def get_bremicker_by_time(conn: AsyncIOMotorClient, box_id=None, start_date=None, end_date=None, start_hour='0:00', end_hour='23:00', grouper_freq='10Min'):
    print("[BREMICKER] start fetching bremicker")
    df = await get_bremicker(conn, start_date, end_date, grouper_freq=grouper_freq)
    if df is None or df.shape[0] < 3:
        yesterday = datetime.datetime.strftime(datetime.datetime.now() - timedelta(1), '%Y-%m-%d')
        df = await get_bremicker(conn, start_date=yesterday)
    df = df.reset_index()
    df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")
    df = df.set_index('time')
    df = df.between_time(start_hour, end_hour)
    if df.shape[0] == 0:
        print("[BREMICKER] start and end time not found. Fetching yesterday")
        yesterday = datetime.datetime.strftime(datetime.datetime.now() - timedelta(1), '%Y-%m-%d')
        return await get_bremicker_by_time(conn, start_date=yesterday, end_date=yesterday, start_hour=start_hour, end_hour=end_hour)
    df.index = df.index.strftime("%Y-%m-%d %H:%M")
    if box_id is not None:
        return df[[box_id]]
    return df


async def fetch_bremicker(conn: AsyncIOMotorClient, start_date=None, end_date=None):
    print('[BREMICKER] Fetching data from Bremicker server')
    print(start_date)
    print(end_date)
    params = {
        'key': BREMICKER_API_KEY,
        'from': start_date.strftime("%Y-%m-%d"),
        'to': end_date.strftime("%Y-%m-%d"),
    }
    try:
        response = requests.get(BREMICKER_URL, params=params)
        if response is None:
            raise Exception('[BREMICKER] Fetched data from server returned nothing - None')
        response = response.json()
        if len(response) == 0:
            raise Exception('[BREMICKER] Fetched data from server returned nothing')
            # response = await insert_bremicker(conn, [{'measure_date': start_date, 'data': []}])
            # return response

        response = await format_bremicker(response)
        await insert_bremicker(conn, response)
        return response
    except JSONDecodeError as error:
        print("[BREMICKER] JSON decoding error from server. Trying to fetch again...")
        return await fetch_bremicker(conn, start_date, end_date)
        # raise Exception('[BREMICKER] Error in json decoding: %s' % error)
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail='Error in fetching Bremicker: %s' % str(e))


async def insert_bremicker(conn: AsyncIOMotorClient, data):
    print("[MONGODB] Saving Bremicker data")
    try:
        for item in data:
            await conn[database_name][bremicker_collection_name].find_one_and_replace({'measure_date': item['measure_date']}, item, upsert=True)
            print("[MONGODB] Successfully saved bremicker data of %s" % item['measure_date'])
    except Exception as e:
        raise Exception('[BREMICKER] Error in saving data to db: %s' % str(e))
    else:
        print("[MONGODB] Bremicker data successfully saved!")
        return data


async def format_bremicker(data):
    print("[BREMICKER] Formatting data now")
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d")
    print("[BREMICKER] Grouping data now")
    result = []
    for date, df in df.groupby('date'):
        date = datetime.datetime.combine(date, datetime.time.min)
        entry = {'measure_date': date,
                 'data': df[['time', 'boxID', 'entryVelocity', 'averageVelocity']].to_dict(orient='records')}
        result.append(entry)
    print("[BREMICKER] Successfully formatted data")
    return result
