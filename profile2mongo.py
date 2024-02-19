from os import getenv
from pandas import read_csv
import argparse

import mongo

connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
mongo_api = mongo.MongoAPI(connection_string)

def profile2mongo(filename):
    df = read_csv(filename, sep='\t')
    df = df[['ID']].assign(
                    profile=df.set_index(['ID']).to_dict(orient='records')
    )
    for _index, row in df.iterrows():
        # Each rows' to_dict() will be a MongoDB document
        document = row.to_dict()
        print(document['ID'])
        for key, value in document['profile'].items():
            converted = None
            try:
                converted = int(value)
            except ValueError:
                print(f"Key {key}: value {value} could not cenvert.")
            if converted:
                try: 
                    assert type(value) == type(converted)
                    print(f"{key}: {type(value)} == {type(converted)}")
                except AssertionError:
                    print(f"{key}: value {value} has a problem:")
                    print(f"Original type is {type(value)}, converted type is {type(converted)}.")
        print()
        # result = mongo_api.db.samples.insert_one(document)
        # assert result.acknowledged == True
        # print(result.inserted_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='profile2mongo',
                    description='Import an allele profile TSV file to MongoDB',
    )

    parser.add_argument('filename')
    args = parser.parse_args()
    profile2mongo(args.filename)