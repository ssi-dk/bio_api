from os import getenv
from pandas import read_csv
import argparse
import pymongo

import client_functions

def profile2mongo(db, filename: str, collection: str='samples', max_items:int=None):
    df = read_csv(filename, sep='\t')
    df = df[['name']].assign(
                    profile=df.set_index(['name']).to_dict(orient='records')
    )
    inserted_ids = list()
    for _index, row in df.iterrows():
        if max_items and (_index > max_items):
            print(f"Reached maximum of {max_items} items.")
            break

        # Check if document with given 'name' already exists, skip if true
        existing_document = db[collection].find_one({'name': row['name']})
        if existing_document:
            _id = str(existing_document['_id'])
            print(f"Document with name = '{row['name']}' already exists and has _id {_id}")
            inserted_ids.append(_id)
            continue

        # Each rows' to_dict() will be a MongoDB document
        document = row.to_dict()

        # Make sure that all numberish values are ints
        for key, value in document['profile'].items():
            try:
                document['profile'][key] = int(value)
            except ValueError:
                pass

        result = db[collection].insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='profile2mongo',
                    description='Import an allele profile TSV file to MongoDB',
    )

    parser.add_argument('filename')
    parser.add_argument('--max_items', type=int, help="Limit the number of items to process")
    parser.add_argument('--dmx', help="Calculate dist matrix", action="store_true")
    args = parser.parse_args()
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Max items: {args.max_items}")
    max_items = int(args.max_items) if args.max_items else None
    inserted_ids = profile2mongo(db, args.filename, max_items=max_items)
    #inserted_ids = profile2mongo(db, args.filename)
    print("These are the _id strings of the MongoDB documents:")
    print(inserted_ids)

    if args.dmx:
        print("--dmx option set; calculating distance matrix")
        response = client_functions.call_dmx_from_mongodb(
            collection='samples',
            seqid_field_path='name',
            profile_field_path='profile',
            mongo_ids=inserted_ids)
        print("Response:")
        print(response)
        print("Response as JSON:")
        print(response.json())