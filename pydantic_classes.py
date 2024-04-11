import typing

from pydantic import BaseModel



# Request classes

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


class DistanceMatrixRequest(BaseModel):
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
    seq_mongo_ids: list


class HCTreeCalcRequest(BaseModel):
    """
    Parameters for a REST request for a tree calculation based on hierarchical clustering.
    Distances are taken directly from the request.
    """
    dmx_job: str
    method: str



# Response classes

class Message(BaseModel):
    detail: str


class CommonPOSTResponse(BaseModel):
    """Common response class for all clculation responses (both POST and GET)"""
    job_id: str
    created_at: str
    status: str


class CommonGETResponse(CommonPOSTResponse):
    finished_at: typing.Optional[str]  # Optional since if job not completed the field will not exist


class Neighbor(BaseModel):
    id: str
    diff_count: int


class NearestNeighborsGETResponse(NearestNeighborsRequest, CommonGETResponse):
    result: typing.Optional[list[Neighbor]]


class DistanceMatrixGETResponse(DistanceMatrixRequest, CommonGETResponse):
    result: typing.Optional[dict]


class HCTreeCalcGETResponse(HCTreeCalcRequest, CommonGETResponse):
    result: typing.Optional[str]