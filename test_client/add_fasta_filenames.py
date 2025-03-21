from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json
import string
import random

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def add_fasta_filenames(
            db,
            collection: str='samples'
            ):

    upserted_ids = list()

    result = db[collection].update_many({}, 
        { 
            "$set": { "categories.contigs.summary.data" : '/some/file/location/' + id_generator(size=10) + '.fasta' }
        } 
    )

    print(result)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=str, help="name of collection to update", default='campy_2019')
    args = parser.parse_args()
    connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    print(connection_string)
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    updated_ids = add_fasta_filenames(
        db,
        collection=args.collection,
        )
