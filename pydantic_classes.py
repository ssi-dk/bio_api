import typing

from pydantic import BaseModel


class NearestNeighborsRequest(BaseModel):
    """
    Parameters for a REST request for a nearest neighbors calculation.
    """
    seq_collection: str
    filtering: typing.Optional[dict] = None
    profile_field_path: str
    input_mongo_id: str
    cutoff: int
    unknowns_are_diffs: bool

class DMXFromMongoRequest(BaseModel):
    """
    Parameters for a REST request for a distance calculation.

    seq_collection: collection to find sequences in
    seqid_field_path: field path in dotted notation which contains the 'sequence id' the user wants to see
    profile_field_path: field path in dotted notation which contains the cgMLST allele profiles
    mongo_ids: the  _id strings for the desired sequence documents
    """
    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    mongo_ids: list

class HCTreeCalcFromDMXJobRequest(BaseModel):
    """
    Parameters for a REST request for a tree calculation based on hierarchical clustering.
    Distances are taken directly from the request.
    """
    dmx_job: str
    method: str