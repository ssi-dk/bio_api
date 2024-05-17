from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json

import client_functions

def import_profiles(
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
        document.update(dictified_seqid_path)
        dictified_profile_path = client_functions.dictify_path(profile_field_path, document.pop('profile'))
        document.update(dictified_profile_path)
        dictified_species_path = client_functions.dictify_path(species_field_path, species)
        document.update(dictified_species_path)

        result = db[collection].insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

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
    # species_field_path will be used to filter sequences so we know that all samples where we add an allele profile has this species.
    parser.add_argument('--species_field_path',
                        type=str,
                        help="path for species field - dots are translated into nested fields",
                        default='categories.species_detection.summary.species')
    parser.add_argument('--species', type=str, help="Species to insert in species_field_path", default='Salmonella enterica')
    parser.add_argument('--max_items', type=int, help="limit the number of items to import")
    args = parser.parse_args()
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    print(f"Import to collection: {args.collection}")
    print(f"MongoDB field containing cgMLST profile: {args.profile_field_path}")
    print(f"Max items to import: {args.max_items}")
    max_items = int(args.max_items) if args.max_items else None

    # updated_ids = import_profiles(
    #     db,
    #     args.filename,
    #     collection=args.collection,
    #     profile_field_path=args.profile_field_path,
    #     species_field_path=args.species_field_path,
    #     species=args.species,
    #     max_items=max_items
    #     )
    # print("These are the _id strings of the MongoDB documents:")
    # print(json.dumps(updated_ids))