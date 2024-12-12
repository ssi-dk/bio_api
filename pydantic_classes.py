import typing
from enum import Enum

from pydantic import BaseModel #creates instances of classes ensuring the correct parameters and type

# the parameters SOFI specifies when it creates the call (client)

# Request classes

class NearestNeighborsRequest(BaseModel):
    """
    Parameters for a REST request for a nearest neighbors calculation.
    """
    seq_collection: str
    # The filtering dict must exist, at there must at least be a filter on species
    filtering: dict
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
    seq_mongo_ids: the  _id strings for the desired sequence documents
    """
    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    seq_mongo_ids: list | None


class HCTreeCalcRequest(BaseModel):
    """
    Parameters for a REST request for a tree calculation based on hierarchical clustering.
    Distances are taken directly from the request.
    """
    dmx_job: str
    # See https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    method: typing.Literal["single", "complete", "average", "weighted", "centroid", "median", "ward"]



# Response classes

class Message(BaseModel):
    detail: str


class Status(str, Enum):
    init = "init"
    completed = "completed"
    error = "error"


class CommonPOSTResponse(BaseModel):
    """Common response base class for all calculation responses (both POST and GET)"""
    job_id: str
    created_at: str
    status: Status


class CommonGETResponse(CommonPOSTResponse):
    finished_at: typing.Optional[str]  # Optional since if job not completed the field will not exist


class Neighbor(BaseModel):
    id: str
    diff_count: int


class NearestNeighborsGETResponse(NearestNeighborsRequest, CommonGETResponse):
    result: typing.Any


class DistanceMatrixResult(BaseModel):
    seq_to_mongo: dict
    distances: typing.Optional[str] = None

class DistanceMatrixGETResponse(DistanceMatrixRequest, CommonGETResponse):
    result: typing.Any


class HCTreeCalcGETResponse(HCTreeCalcRequest, CommonGETResponse):
    result: typing.Any