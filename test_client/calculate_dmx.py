from os import getenv
import argparse
import pymongo
from bson import ObjectId

import client_functions

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='calculate_dmx',
                    description="Calculate a istance matrix for testing."
    )

    parser.add_argument('mongo_ids', type=str, help="ObjecIDs as strings separated by commas")
    parser.add_argument('--seq_collection', type=str, help="name of collection that contains sequence documents", default='samples')
    parser.add_argument('--seqid_field_path', type=str, help="path for seqid field - dots are translated into nested fields", default='categories.sample_info.summary.sofi_sequence_id')
    parser.add_argument('--profile_field_path', type=str, help="path for profile field - dots are translated into nested fields", default='categories.cgmlst.report.alleles')
    parser.add_argument('--species_field_path', type=str, help="path for species field - dots are translated into nested fields", default='categories.species_detection.summary.species ')
    parser.add_argument('--species', type=str, help="Species to search for", default='Salmonella enterica')
    args = parser.parse_args()
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Sequences collection: {args.seq_collection}")
    print(f"MongoDB field containing 'user' sequence id: {args.seqid_field_path}")
    print(f"MongoDB field containing cgMLST profile: {args.profile_field_path}")

    mongo_str_all: str = args.mongo_ids
    string_list: str = mongo_str_all.split(',')
    print(f"Mongo IDs to search for: {string_list}")
    object_ids = [ObjectId(s) for s in string_list]

    # Make sure we can actually find those documents
    assert db[args.seq_collection].count_documents({'_id': {'$in': object_ids}}) == len(string_list)

    # Initialize the calculation
    response = client_functions.call_dmx_from_mongodb(
        seq_collection=args.seq_collection,
        seqid_field_path=args.seqid_field_path,
        profile_field_path=args.profile_field_path,
        mongo_ids=string_list)
    print("Response:")
    print(response)
    print("Response as JSON:")
    print(response.json())