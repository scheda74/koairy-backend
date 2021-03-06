import datetime
from ..db.mongodb import AsyncIOMotorClient
from ..core.config import (
    database_name,
    caqi_emission_collection_name,
    raw_emission_collection_name,
    training_data_collection_name,
    simulated_traffic_collection_name
)


async def get_caqi_emissions_for_sim(conn: AsyncIOMotorClient, sim_id: str):
    emission_doc = await conn[database_name][caqi_emission_collection_name].find_one({"sim_id": sim_id},
                                                                                     projection={"id": False})
    if emission_doc:
        return emission_doc
    else:
        return None
        # raise RuntimeError(f" Couldn't find caqi emissions for specified simulation,"
        #                    f" sim_id={sim_id} emission_id={emission_doc}")


async def get_raw_emissions_from_sim(conn: AsyncIOMotorClient, sim_id: str):
    try:
        emission_doc = await conn[database_name][raw_emission_collection_name].find_one({"sim_id": sim_id},
                                                                                        projection={"_id": False})

        # if emission_doc is None or len(emission_doc["emissions"]) == 0:
        #     await drop_simulation_data(conn, sim_id)
        #     raise Exception("[MONGODB] Raw emissions empty")
    except Exception as e:
        raise Exception("[MONGODB] Error while fetching from database: %s" % str(e))
    else:
        return emission_doc


async def get_simulated_traffic_from_sim(conn: AsyncIOMotorClient, sim_id: str):
    try:
        emission_doc = await conn[database_name][simulated_traffic_collection_name].find_one({"sim_id": sim_id},
                                                                                        projection={"_id": False})

        # if emission_doc is None or len(emission_doc["emissions"]) == 0:
        #     await drop_simulation_data(conn, sim_id)
        #     raise Exception("[MONGODB] Raw emissions empty")
    except Exception as e:
        raise Exception("[MONGODB] Error while fetching from database: %s" % str(e))
    else:
        return emission_doc

async def insert_caqi_emissions(conn: AsyncIOMotorClient, sim_id: str, emissions: dict):
    print("[MONGODB] Saving calculated CAQI emissions")
    caqi_doc = {"emissions": emissions, "created_at": datetime.datetime.utcnow(), "sim_id": sim_id}
    try:
        await conn[database_name][caqi_emission_collection_name].insert_one(caqi_doc)
    except Exception as e:
        raise Exception("[MONGODB] Error while saving to database: %s" % str(e))


async def insert_raw_emissions(conn: AsyncIOMotorClient, sim_id: str, emissions: dict):
    print("[MONGODB] Saving simulated emissions")
    raw_doc = {"emissions": emissions, "created_at": datetime.datetime.utcnow().strftime('%Y-%m-%d'), "sim_id": sim_id}
    try:
        await conn[database_name][raw_emission_collection_name].insert_one(raw_doc)
    except Exception as e:
        raise Exception("[MONGODB] Error while saving raw emissions to database: %s" % str(e))
    else:
        print("[MONGODB] Saving raw emissions successful!")


async def insert_simulated_traffic(conn: AsyncIOMotorClient, sim_id: str, emissions: dict):
    print("[MONGODB] Saving simulated emissions")
    raw_doc = {"emissions": emissions, "created_at": datetime.datetime.utcnow().strftime('%Y-%m-%d'), "sim_id": sim_id}
    try:
        await conn[database_name][simulated_traffic_collection_name].insert_one(raw_doc)
    except Exception as e:
        raise Exception("[MONGODB] Error while saving to simulated traffic to database: %s" % str(e))
    else:
        print("[MONGODB] Saving simulated traffic successful!")


async def insert_aggregated_data(conn: AsyncIOMotorClient, sim_id: str, data: dict):
    print("[MONGODB] Saving aggregated data")
    raw_doc = {"aggregated": data, "created_at": datetime.datetime.utcnow(), "sim_id": sim_id}
    try:
        await conn[database_name][training_data_collection_name].insert_one(raw_doc)
    except Exception as e:
        raise Exception("[MONGODB] Error while saving to database: %s" % str(e))


async def get_aggregated_data_from_sim(conn: AsyncIOMotorClient, sim_id: str):
    print("[MONGODB] Fetching aggregated data")
    try:
        aggregated_data = await conn[database_name][training_data_collection_name].find_one({"sim_id": sim_id}, {"_id": False})
        if aggregated_data:
            return aggregated_data
        else:
            return None
    except Exception as e:
        raise Exception("[MONGODB] Error while fetching from database: %s" % str(e))


async def drop_simulation_data(conn: AsyncIOMotorClient, sim_id: str):
    try:
        await conn[database_name][training_data_collection_name].delete_one({"sim_id": sim_id})
        await conn[database_name][simulated_traffic_collection_name].delete_one({"sim_id": sim_id})
        await conn[database_name][raw_emission_collection_name].delete_one({"sim_id": sim_id})
        return
    except Exception as e:
        raise Exception("[MONGODB] Error while deleting collections: %s" % str(e))