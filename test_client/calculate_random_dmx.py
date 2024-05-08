from os import getenv
import argparse
import pymongo

import client_functions

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='calculate_random_dmx',
                    description="Calculate a random distance matrix for testing."
    )

    parser.add_argument('--sequence_count', type=int, default=10)
    parser.add_argument('--seq_collection', type=str, help="name of collection that contains sequence documents", default='samples')
    parser.add_argument('--seqid_field_path', type=str, help="path for seqid field - dots are translated into nested fields", default='name')
    parser.add_argument('--profile_field_path', type=str, help="path for profile field - dots are translated into nested fields", default='profile')
    parser.add_argument('--species_field_path', type=str, help="path for species field - dots are translated into nested fields", default='species')
    parser.add_argument('--species', type=str, help="Species to search for", default='Salmonella enterica')
    args = parser.parse_args()
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Sequences collection: {args.seq_collection}")
    print(f"MongoDB field containing 'user' sequence id: {args.seqid_field_path}")
    print(f"MongoDB field containing cgMLST profile: {args.profile_field_path}")

    # Find ids based on species and the desired sequence count
    pipeline = [
        { '$sample': { 'size': args.sequence_count } },
        { '$project': { '_id': 1 } }
    ]
    mongo_cursor = db[args.seq_collection].aggregate(pipeline)
    mongo_ids = [ str(s['_id']) for s in mongo_cursor ]
    print("Mongo IDs:")
    print(mongo_ids)

    # Initialize the calculation
    response = client_functions.call_dmx_from_mongodb(
        seq_collection=args.seq_collection,
        seqid_field_path=args.seqid_field_path,
        profile_field_path=args.profile_field_path,
        mongo_ids=mongo_ids)
    print("Response:")
    print(response)
    print("Response as JSON:")
    print(response.json())