import pymongo

def strs2ObjectIds(id_strings: list):
    """
    Converts a list of strings to a set of ObjectIds
    """
    output = list()
    for id_str in id_strings:
        output.append(ObjectId(id_str))
    return output


class MongoAPI:
    def __init__(self,
        connection_string: str,
    ):
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()

    async def get_field_data(
            self,
            collection:str,   # MongoDB collection
            mongo_ids:list | None,   # List of MongoDB ObjectIds as str
            field_paths:list, # List of field paths in dotted notation: ['some.example.field1', 'some.other.example.field2']
        ):
        if mongo_ids:
            filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}
            document_count = self.db[collection].count_documents(filter)
            cursor = self.db[collection].find(filter, {field_path: True for field_path in field_paths})
        else:
            document_count = self.db[collection].count_documents({})
            cursor = self.db[collection].find({}, {field_path: True for field_path in field_paths})
        return document_count, cursor