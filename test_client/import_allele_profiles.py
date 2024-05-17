from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json

import pymongo.cursor

import client_functions

def import_profiles(
            db,
            filename: str,
            collection: str,
            profile_field_path: str,
    ):
    
    stu_count = db[collection].count_documents({'categories.cgmlst.report.alleles': {'$exists': 0}})
    print(f"{str(stu_count)} sequences are missing allele profile.")

    sequences_to_update: pymongo.cursor.Cursor
    sequences_to_update = db[collection].find({'categories.cgmlst.report.alleleles': {'$exists': 0}})
    print(sequences_to_update)

    df = read_csv(filename, sep='\t')
    updated_ids = list()
    # for _index, row in df.iterrows():

    #     document = row.to_dict()

    #     # Make sure that all numberish values are ints
    #     for key, value in document['profile'].items():
    #         try:
    #             document['profile'][key] = int(value)
    #         except ValueError:
    #             pass

    #     result = db[collection].insert_one(document)
    #     assert result.acknowledged == True
    #     updated_ids.append(str(result.inserted_id))
    return updated_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='import_profiles',
                    description=\
                        "Import allele profiles from a .tsv file and add them to existing sequences i MongoDB. " +
                        "The script will add allele profiles to existing samples that has the desired species and " +
                        "does not already have an allele profile. " +
                        "It will continue until either all the samples has got an allele profile or " +
                        "there are no more allele profiles to add."
    )

    parser.add_argument('filename')
    parser.add_argument('--collection', type=str, help="name of collection which contains samples to import allele profiles to", default='samples')
    parser.add_argument('--profile_field_path',
                        type=str,
                        help="path for profile field - dots are translated into nested fields",
                        default='categories.cgmlst.report.alleleles')
    args = parser.parse_args()
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://localhost:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Import to collection: {args.collection}")
    print(f"MongoDB field containing cgMLST profile: {args.profile_field_path}")

    updated_ids = import_profiles(
        db,
        args.filename,
        collection=args.collection,
        profile_field_path=args.profile_field_path,
        )
    print("These are the _id strings of the MongoDB documents:")
    print(json.dumps(updated_ids))