from bson import ObjectId

#MOCK ObjectIDs
MOCK_INPUT_ID = ObjectId("65f000abc123abc123abc111")
MOCK_JOB_ID = ObjectId("65f000abc123abc123abc123")

# Mock MongoAPI config section
MOCK_MONGO_CONFIG = {
    "seq_collection": "sequences",
    "profile_field_path": "cgmlst.profile",
    "cutoff": 2,
    "filtering": {"species": "Ecoli"},
    "unknowns_are_diffs": True
}

# Input document returned by query_mongodb_for_input_profile
MOCK_INPUT_SEQUENCE = {
    "_id": MOCK_INPUT_ID,
    "cgmlst": {
        "profile": {
            "locus1": "1",
            "locus2": "2"
        }
    }
}

# Neighbor document for aggregation
MOCK_NEIGHBOR_SEQUENCE = {
    "_id": ObjectId("65f000abc123abc123abc222"),
    "cgmlst": {
        "profile": {
            "locus1": "1",
            "locus2": "3"
        }
    }
}

# POST request body
NN_REQUEST_BODY = {
    "input_mongo_id": str(MOCK_INPUT_ID),
    "filtering": {"species": "Ecoli"},
    "cutoff": 2,
    "unknowns_are_diffs": True
}

# GET response from to_dict
MOCK_RECALL_DICT = {
    "job_id": str(MOCK_JOB_ID),
    "created_at": "2025-03-25T10:00:00Z",
    "status": "completed",
    "input_mongo_id": str(MOCK_INPUT_ID),
    "filtering": {"species": "Ecoli"},
    "cutoff": 2,
    "unknowns_are_diffs": True,
    "result": [
        {"id": "65f000abc123abc123abc222", "diff_count": 1},
        {"id": "65f000abc123abc123abc333", "diff_count": 2}
    ]
}
