from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json

from client_functions import dictify_path, recursive_merge

def add_fasta_filenames(
            db,
            collection: str='samples'
            ):

    upserted_ids = list()

    result = db[collection].update_many({}, 
        { 
            "$set": { "categories.contigs.summary.data" : "test_file.fasta" } 
        } 
    )

    assert result.acknowledged == True
    upserted_ids.append(str(result.upserted_id))
    return upserted_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=str, help="name of collection to update", default='samples')
    args = parser.parse_args()
    connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    print(connection_string)
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    updated_ids = add_fasta_filenames(
        db,
        collection=args.collection,
        )
    print("These are the _id strings of the MongoDB documents:")
    print(json.dumps(updated_ids))
