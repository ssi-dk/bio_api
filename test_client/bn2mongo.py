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

def bn2mongo(
            db,
            tsv_filename: str,
            collection: str='samples',
            seqid_field_path: str='name',
            profile_field_path: str='profile',
            species_field_path: str='species',
            species: str='Salmonella enterica',
            max_items: int=None):
    df = read_csv(tsv_filename, sep='\t')
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
                    prog='bn2mongo',
                    description="Import a TSV file with analysis data to MongoDB. " + 
                        "The first column in the file must contain the user-oriented sequence id, and this column MUST be named 'name'. " +
                        "Apart from the data file the script will also need a JSON file containing the mappings from the TSV file's column names " +
                        "to field paths in MongoDB. " +
                        "The specific use case for the script is importing a data file exported from BioNumerics."
    )

    parser.add_argument('tsv_filename')
    parser.add_argument('--collection', type=str, help="name of collection to import to", default='samples')
    parser.add_argument('--max_items', type=int, help="limit the number of items to import")
    args = parser.parse_args()
    connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Import to collection: {args.collection}")
    print(f"Max items to import: {args.max_items}")
    max_items = int(args.max_items) if args.max_items else None
    inserted_ids = bn2mongo(
        db,
        args.tsv_filename,
        collection=args.collection,
        max_items=max_items
        )
    print("These are the _id strings of the MongoDB documents:")
    print(json.dumps(inserted_ids))