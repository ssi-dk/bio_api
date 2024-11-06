from os import getenv

import pymongo

client = pymongo.MongoClient(
    username="admin",
    password=input("Mongo password: "),
    directConnection=True
)
db = client['sofi-dev']
collections = db.list_collections()
print(list(collections))