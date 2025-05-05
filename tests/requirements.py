# Config.py

from bson import ObjectId

# === MOCK OBJECT IDs === #

MOCK_INPUT_ID = ObjectId("65f000abc123abc123abc111")
MOCK_JOB_ID = ObjectId("65f000abc123abc123abc123")

MOCK_NEIGHBOR_ID_1 = ObjectId("65f000abc123abc123abc222")
MOCK_NEIGHBOR_ID_2 = ObjectId("65f000abc123abc123abc333")
MOCK_NEIGHBOR_ID_missing = ObjectId("65f000abc123abc123abc999")

# === Correct NN Config === #

MOCK_MONGO_CONFIG = {
    "seq_collection": "samples",
    "profile_field_path": "categories.cgmlst.report.alleles",
    "allele_path": "categories.cgmlst.report.allele_array",
    "digest_path": "categories.cgmlst.report.schema.digest",
    "call_pct_path": "categories.cgmlst.summary.call_percent",
    "cutoff": 2,
    "filtering": {},
    "unknowns_are_diffs": True
}

# === Input Sequence (matches config structure) === #

MOCK_INPUT_SEQUENCE = {
    "_id": MOCK_INPUT_ID,
    "categories": {
        "cgmlst": {
            "summary": {"call_percent": 100},
            "report": {
                "allele_array": [1,2],
                "alleles": {
                    "locus1": "1",
                    "locus2": "2"
                },
                "schema": {
                    "digest": 1
                }
            }
        }
    }
}

# === Neighbor Sequence (1 difference) === #

MOCK_NEIGHBOR_SEQUENCE = {
    "_id": MOCK_NEIGHBOR_ID_1,
    "categories": {
        "cgmlst": {
            "summary": {"call_percent": 100},
            "report": {
                "allele_array": [1,3],
                "alleles": {
                    "locus1": "1",
                    "locus2": "3"
                },
                "schema": {
                    "digest": 1
                }
            }
        }
    }
}

# === Another Neighbor (2 differences) === #

MOCK_NEIGHBOR_SEQUENCE_2 = {
    "_id": MOCK_NEIGHBOR_ID_2,
    "categories": {
        "cgmlst": {
            "summary": {"call_percent": 100},
            "report": {
                "allele_array": [9,3],
                "alleles": {
                    "locus1": "9",
                    "locus2": "3"
                },
                "schema": {
                    "digest": 1
                }
            }
        }
    }
}

# === POST request to /nearest_neighbors === #

NN_REQUEST_BODY = {
    "input_mongo_id": str(MOCK_INPUT_ID),
    "filtering": MOCK_MONGO_CONFIG["filtering"],
    "cutoff": MOCK_MONGO_CONFIG["cutoff"],
    "unknowns_are_diffs": MOCK_MONGO_CONFIG["unknowns_are_diffs"]
}

# === Simulated GET Response === #

MOCK_RECALL_DICT = {
    "job_id": str(MOCK_JOB_ID),
    "created_at": "2025-03-25T10:00:00Z",
    "status": "completed",
    "input_mongo_id": str(MOCK_INPUT_ID),
    "filtering": MOCK_MONGO_CONFIG["filtering"],
    "cutoff": MOCK_MONGO_CONFIG["cutoff"],
    "unknowns_are_diffs": MOCK_MONGO_CONFIG["unknowns_are_diffs"],
    "result": [
        {"id": str(MOCK_NEIGHBOR_ID_1), "diff_count": 1},
        {"id": str(MOCK_NEIGHBOR_ID_2), "diff_count": 2}
    ]
}
