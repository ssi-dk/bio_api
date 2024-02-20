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
    inserted_ids = list()
    for _index, row in df.iterrows():

        # Each rows' to_dict() will be a MongoDB document
        document = row.to_dict()

        # Make sure that all numberish values are ints
        for key, value in document['profile'].items():
            try:
                document['profile'][key] = int(value)
            except ValueError:
                pass

        result = mongo_api.db.samples.insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='profile2mongo',
                    description='Import an allele profile TSV file to MongoDB',
    )

    parser.add_argument('filename')
    args = parser.parse_args()
    inserted_ids = profile2mongo(args.filename)
    print("These are the _id strings of the created MongoDB documents:")
    print(inserted_ids)