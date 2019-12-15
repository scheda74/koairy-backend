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

    try:
        docs = await conn[database_name][bremicker_collection_name].count_documents({"$and": [{"measure_date": {"$gte": start_date}}, {"measure_date": {"$lte": end_date}}]})
        if docs == 0:
            print('Fetching from %s to %s' % (start_date, end_date))
            await fetch_bremicker(conn, start_date, end_date)

        result = []
        async for document in conn[database_name][bremicker_collection_name].find({"$and": [{"measure_date": {"$gte": start_date}}, {"measure_date": {"$lte": end_date}}]}):
            if document is None:
                document = await fetch_bremicker(conn, document['measure_date'], document['measure_date'])
            # print(document)
            print('fetching data from %s' % document['measure_date'].strftime('%Y-%m-%d'))
            df = pd.DataFrame.from_dict(document['data'])
            df['date'] = document['measure_date'].strftime('%Y-%m-%d')
            df['time'] = df[['date', 'time']].apply(lambda x: pd.to_datetime(' '.join(x)), axis=1)
            df = df.groupby([pd.Grouper(key='time', freq=grouper_freq), 'boxID']).size().reset_index()
            df['time'] = df['time'].astype(str)
            df = df.set_index('time').rename(columns={0: 'numberOfVehicles'})
            df = df.reset_index()
            # df = pd.pivot_table(df, index=['time'], values='numberOfVehicles', columns='boxID')
            df = df.pivot(index='time', values='numberOfVehicles', columns='boxID').reset_index().rename_axis(None, axis=1)
            df = df.set_index('time')
            result.append(df)
        df = pd.concat(result).fillna(0)
        print(df)
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail='[BREMICKER] Error in fetching from db: %s' % str(e))


async def get_bremicker_by_time(conn: AsyncIOMotorClient, box_id=None, start_date=None, end_date=None, start_hour='0:00', end_hour='23:00', grouper_freq='10Min'):
    df = await get_bremicker(conn, start_date, end_date, grouper_freq=grouper_freq)
    if df is None or df.shape[0] < 3:
        yesterday = datetime.datetime.strftime(datetime.datetime.now() - timedelta(1), '%Y-%m-%d')
        df = await get_bremicker(conn, start_date=yesterday)
    df = df.reset_index()
    df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")
    df = df.set_index('time')
    df = df.between_time(start_hour, end_hour)
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
            raise HTTPException(status_code=500, detail='[BREMICKER] Fetched data from server returned nothing - None')
        response = response.json()
        if len(response) == 0:
            # raise HTTPException(status_code=500, detail='[BREMICKER] Fetched data from server returned nothing')
            response = await insert_bremicker(conn, [{'measure_date': start_date, 'data': []}])
            return response

        response = await format_bremicker(response)
        await insert_bremicker(conn, response)
        return response
    except JSONDecodeError as error:
        raise HTTPException(status_code=500, detail='[BREMICKER] Error in json decoding: %s' % error)
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail='Error in fetching Bremicker: %s' % str(e))


async def insert_bremicker(conn: AsyncIOMotorClient, data):
    print("[MONGODB] Saving Bremicker data")
    try:
        for item in data:
            await conn[database_name][bremicker_collection_name].find_one_and_replace({'measure_date': item['measure_date']}, item, upsert=True)
            print("[MONGODB] Successfully saved bremicker data of %s" % item['measure_date'])
    except Exception as e:
        raise HTTPException(status_code=500, detail='[BREMICKER] Error in saving data to db: %s' % str(e))
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

# async def get_latest_bremicker(conn: AsyncIOMotorClient, start_hour='0:00', end_hour='23:00'):
#     df = await get_bremicker(conn)
#     if df is None or df.shape[0] < 3:
#         yesterday = datetime.datetime.strftime(datetime.datetime.now() - timedelta(1), '%Y-%m-%d')
#         df = await get_bremicker(conn, start_date=yesterday)
#     df = df.reset_index()
#     df['time'] = pd.to_datetime(df['time'], format="%Y-%m-%d %H:%M")
#     df = df.set_index('time')
#     df = df.between_time(start_hour, end_hour)
#     df.index = df.index.strftime("%Y-%m-%d %H:%M")
#     return df


# async def fetch_latest_bremicker(db, start_hour=None, end_hour=None):
#     df_traffic = await get_current_bremicker_by_time(db, start_hour=start_hour, end_hour=end_hour)
#     # if there are 2 hours or less (around midnight) take yesterday!
#     if df_traffic is None or df_traffic.shape[0] < 3:
#         yesterday = datetime.datetime.strftime(datetime.datetime.now() - timedelta(1), '%Y-%m-%d')
#         df_traffic = await get_current_bremicker_by_time(db, start_date=yesterday, start_hour=start_hour,
#                                                          end_hour=end_hour)
#     return df_traffic
#
#
# async def get_bremicker_by_time(conn: AsyncIOMotorClient, box_id, start_date='2019-08-01', end_date='2019-11-01', start_hour='07:00', end_hour='10:00'):
#     box_id = int(box_id)
#     df_traffic = await get_bremicker(conn, start_date, end_date, grouper_freq='H')
#     if df_traffic is None:
#         return None
#     # if bremicker['data']:
#     #     df_traffic = pd.DataFrame(pd.read_json(bremicker['data']))
#     # elif bremicker is not None:
#     #     df_traffic = pd.DataFrame(pd.read_json(bremicker))
#     # else:
#     #     return None
#     # df_traffic.index.name = 'time'
#     df = df_traffic.reset_index()[['time', box_id]]
#     # df = df.groupby([pd.Grouper(key='time', freq='H')]).sum()
#     df = df.reset_index()
#     # mask = (df['time'] >= start_date) & (df['time'] <= end_date)
#     # df = df.loc[mask].set_index('time')
#     return df.between_time(start_hour, end_hour)


# async def get_current_bremicker_by_time(conn: AsyncIOMotorClient, start_date=None, end_date=None, start_hour=None, end_hour=None):
#     try:
#         print('[BREMICKER] Start fetching bremicker data...')
#         bremicker = await fetch_current_bremicker(conn, start_date, end_date)
#     except Exception as e:
#         raise Exception('[BREMICKER] fetching not successful! %s' % str(e))
#     if bremicker is not None:
#         df_traffic = pd.DataFrame(pd.read_json(bremicker))
#         df_traffic.index.name = 'time'
#         if start_hour is None or end_hour is None:
#             return df_traffic
#         else:
#             return df_traffic.between_time(start_hour, end_hour)
#     else:
#         return None
#
#
# async def get_latest_bremicker_by_box_id(conn: AsyncIOMotorClient, box_id=672):
#     df_traffic = await get_current_bremicker_by_time(conn)
#     if df_traffic is not None:
#         # print(df_traffic)
#         df_traffic = df_traffic[int(box_id)]
#         # return df_traffic.iloc[[-1]]
#         return df_traffic
#     else:
#         return None
#
#
# ### NOTE: Fetch data from bremicker
# async def fetch_bremicker(conn: AsyncIOMotorClient, start_date='2019-06-20', end_date=None):
#     start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
#     if end_date is not None:
#         end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
#     else:
#         end_date = datetime.date.today()
#     print(start_date)
#     print(end_date)
#     params = {
#         'key': BREMICKER_API_KEY,
#         'from': start_date,
#         'to': end_date,
#     }
#     try:
#         response = requests.get(BREMICKER_URL, params=params)
#         response = response.json()
#         response = await format_bremicker(response)
#         await insert_bremicker(conn, start_date, response)
#     except JSONDecodeError as error:
#         print('error in json decoding: %s' % error)
#         raise Exception('Error while decoding bremicker response: %s' % error)
#     except Exception as e:
#         raise Exception('Error while fetching bremicker: %s ' % str(e))
#     else:
#         return response


# if start_date is not None:
#     start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
# else:
#     start_date = datetime.date.today()
# if end_date is not None:
#     end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
# else:
#     end_date = datetime.date.today()


# async def get_bremicker(conn: AsyncIOMotorClient, start_date=None, end_date=None, grouper_freq='10Min'):
#     if start_date is not None:
#         start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
#     else:
#         start_date = datetime.datetime.today().date()
#
#     if end_date is not None:
#         end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
#     else:
#         end_date = datetime.datetime.today().date()
#
#     docs = await conn[database_name][bremicker_collection_name].count_documents({})
#     if docs == 0:
#         await fetch_bremicker(conn, start_date, end_date)
#
#     current_date = start_date
#     result = []
#     while current_date <= end_date:
#         measure_date = current_date.strftime("%Y-%m-%d")
#         print('getting data from %s ' % measure_date)
#         try:
#             data = await conn[database_name][bremicker_collection_name].find_one({'measure_date': measure_date}, projection={"_id": False})
#         except Exception as e:
#             raise HTTPException(status_code=500, detail='[BREMICKER] Error in fetching from db: %s' % str(e))
#         if data is not None:
#             df = pd.DataFrame.from_dict(data['data'])
#             df['date'] = data['measure_date']
#             df['time'] = df[['date', 'time']].apply(lambda x: pd.to_datetime(' '.join(x)), axis=1)
#             df = df.groupby([pd.Grouper(key='time', freq=grouper_freq), 'boxID']).size().reset_index()
#             df['time'] = df['time'].astype(str)
#             df = df.set_index('time').rename(columns={0: 'numberOfVehicles'})
#             df = pd.pivot_table(df, index=['time'], values='numberOfVehicles', columns='boxID')
#             result.append(df)
#         elif data is not None and len(data['data']) == 0:
#             continue
#         else:
#             print('data is none ?!')
#             print('needs fetching now')
#             print('fetching data from %s ' % measure_date)
#             await fetch_bremicker(conn, measure_date, measure_date)
#             continue
#         current_date = current_date + relativedelta(days=1)
#     # if needs_fetching:
#     #     print('start_date: %s' % start_date)
#     #     print('end_date: %s' % end_date)
#
#         # return await get_bremicker(conn, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), grouper_freq)
#     df = pd.concat(result).fillna(0)
#     print(df)
#     return df