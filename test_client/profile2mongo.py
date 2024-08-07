from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json

import client_functions

def recursive_merge(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = recursive_merge(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1

def profile2mongo(
            db,
            filename: str,
            collection: str='samples',
            seqid_field_path: str='name',
            profile_field_path: str='profile',
            species_field_path: str='species',
            species: str='Salmonella enterica',
            max_items: int=None):
    df = read_csv(filename, sep='\t')
    df = df[['name']].assign(
                    profile=df.set_index(['name']).to_dict(orient='records')
    )
    inserted_ids = list()
    for _index, row in df.iterrows():
        if max_items and (_index >= max_items):
            print(f"Reached maximum of {max_items} items.")
            break

        # Each rows' to_dict() will be a MongoDB document
        document = row.to_dict()

        # Make sure that all numberish values are ints
        for key, value in document['profile'].items():
            try:
                document['profile'][key] = int(value)
            except ValueError:
                pass

        # Add some (possibly nested) mongo fields that are important for testing.
        dictified_seqid_path = client_functions.dictify_path(seqid_field_path, document.pop('name'))
        document = recursive_merge(document, dictified_seqid_path)
        dictified_profile_path = client_functions.dictify_path(profile_field_path, document.pop('profile'))
        document = recursive_merge(document, dictified_profile_path)
        dictified_species_path = client_functions.dictify_path(species_field_path, species)
        document = recursive_merge(document, dictified_species_path)

        result = db[collection].insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='profile2mongo',
                    description="Import a .tsv file with allele profiles to MongoDB. " + 
                        "The first column in the file must contain hte user-oriented sequence id, and this column MUST be named 'name'.",
    )

    parser.add_argument('filename')
    parser.add_argument('--collection', type=str, help="name of collection to import to", default='samples')
    parser.add_argument('--seqid_field_path', type=str, help="path for seqid field - dots are translated into nested fields", default='name')
    parser.add_argument('--profile_field_path', type=str, help="path for profile field - dots are translated into nested fields", default='profile')
    parser.add_argument('--species_field_path', type=str, help="path for species field - dots are translated into nested fields", default='species')
    parser.add_argument('--species', type=str, help="Species to insert in species_field_path", default='Salmonella enterica')
    parser.add_argument('--max_items', type=int, help="limit the number of items to import")
    parser.add_argument('--dmx', help="calculate a distance matrix with the imported profiles", action="store_true")
    args = parser.parse_args()
    connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Import to collection: {args.collection}")
    print(f"MongoDB field containing 'user' sequence id: {args.seqid_field_path}")
    print(f"MongoDB field containing cgMLST profile: {args.profile_field_path}")
    print(f"Max items to import: {args.max_items}")
    max_items = int(args.max_items) if args.max_items else None
    inserted_ids = profile2mongo(
        db,
        args.filename,
        collection=args.collection,
        seqid_field_path=args.seqid_field_path,
        profile_field_path=args.profile_field_path,
        species_field_path=args.species_field_path,
        species=args.species,
        max_items=max_items
        )
    print("These are the _id strings of the MongoDB documents:")
    print(json.dumps(inserted_ids))

    if args.dmx:
        print("--dmx option set; calculating distance matrix")
        response = client_functions.call_dmx_from_mongodb(
            seq_collection=args.collection,
            seqid_field_path=args.seqid_field_path,
            profile_field_path=args.profile_field_path,
            mongo_ids=inserted_ids)
        print("Response:")
        print(response)
        print("Response as JSON:")
        print(response.json())