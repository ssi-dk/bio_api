from pydantic import BaseModel

class DMXFromMongoDBRequest(BaseModel):
    """
    collection: collection to find sequences in
    seqid_field_path: field path in dotted notation which contains the 'sequence id' the user wants to see
    profile_field_path: field path in dotted notation which contains the cgMLST allele profiles
    mongo_ids: the  _id strings for the desired sequence documents
    """
    collection: str
    seqid_field_path: str
    profile_field_path: str
    mongo_ids: list

class HCTreeCalcRequest(BaseModel):
    """Represents a REST request for a tree calculation based on hierarchical clustering.
    """
    distances: dict
    method: str