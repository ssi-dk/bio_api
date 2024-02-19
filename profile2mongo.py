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
        result = mongo_api.db.samples.insert_one(row.to_dict())
        assert result.acknowledged == True
        print(result.inserted_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='profile2mongo',
                    description='Import an allele profile TSV file to MongoDB',
    )

    parser.add_argument('filename')
    args = parser.parse_args()
    profile2mongo(args.filename)