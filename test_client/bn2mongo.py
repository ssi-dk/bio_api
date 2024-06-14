from os import getenv
from pandas import read_csv
import argparse
import pymongo
import json

from client_functions import dictify_path, recursive_merge

def bn2mongo(
            db,
            data_filename: str,
            mapping_filename: str,
            collection: str='samples',
            seqid_field_path: str='name',
            profile_field_path: str='profile',
            species_field_path: str='species',
            species: str='Salmonella enterica',
            max_items: int=None):
    
    input_df = read_csv(data_filename, sep=';', encoding='ISO-8859-1')
    
    mapping_df = read_csv(mapping_filename, sep=';', encoding='ISO-8859-1')
    conversion_dict = dict()
    for i in mapping_df.iterrows():
        conversion_entry = i[1].to_dict()
        conversion_dict[conversion_entry['import_column']] = conversion_entry['sofi_fieldname']

    sofi_field_df = read_csv('SOFI_fields.csv', sep=';', encoding='ISO-8859-1')
    print(sofi_field_df)
    sofi_field_dict = dict()
    for _index, row in sofi_field_df.iterrows():
        if not row[2] in ['-', '?']:
            sofi_field_dict[row[1]] = row[2]
    print("SOFI field dict:")
    print(sofi_field_dict)


    inserted_ids = list()
    unnested_document = dict()
    for _index, row in input_df.iterrows():
        if max_items and (_index >= max_items):
            print(f"Reached maximum of {max_items} items.")
            break

        # Each rows' to_dict() will be a MongoDB document
        data_dict = row.to_dict()
        for key, value in data_dict.items():
            sofi_field_name = conversion_dict.get(key)
            if sofi_field_name:
                if sofi_field_name == 'ST':
                    # Need to add a schema name
                    unnested_document[sofi_field_name] = {'some_schema': int(value)}
                else:
                    unnested_document[sofi_field_name] = value
        
        print("Unnested document:")
        print(unnested_document)
        print()

        document = dict()
        for key, value in unnested_document.items():
            dotted_path = sofi_field_dict[key]
            nested_dict = dictify_path(dotted_path, value)
            document = recursive_merge(document, nested_dict)

        print("Nested document:")    
        print(document)
        print()

        result = db[collection].insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='bn2mongo',
                    description="Import a TSV file to SOFI MongoDB structure. " + 
                        "The first column in the file must contain the key. " +
                        "Apart from the data file, the script will also need a file containing the mappings from the data file's column names " +
                        "to SOFI field names as specified in 'SOFI_fields.csv'. " +
                        "The specific use case for the script is importing a data file exported from BioNumerics."
    )

    parser.add_argument('data_filename')
    parser.add_argument('mapping_filename')
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
        args.data_filename,
        args.mapping_filename,
        collection=args.collection,
        max_items=max_items
        )
    print("These are the _id strings of the MongoDB documents:")
    print(json.dumps(inserted_ids))
