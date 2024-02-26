from os import getenv
from pandas import read_csv
import argparse
import pymongo


def profile2mongo(db, filename: str, collection: str='samples'):
    df = read_csv(filename, sep='\t')
    df = df[['name']].assign(
                    profile=df.set_index(['name']).to_dict(orient='records')
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

        result = db[collection].insert_one(document)
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
    connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
    connection = pymongo.MongoClient(connection_string)
    db = connection.get_database()
    print(f"Connection string: {connection_string}")
    inserted_ids = profile2mongo(db, args.filename)
    print("These are the _id strings of the MongoDB documents:")
    print(inserted_ids)