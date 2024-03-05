from pydantic import BaseModel

class DMXFromMongoRequest(BaseModel):
    """
    Parameters for a REST request for a distance calculation.

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
    """
    Parameters for a REST request for a tree calculation based on hierarchical clustering.
    Distances are taken directly from the request.
    """
    distances: dict
    method: str
