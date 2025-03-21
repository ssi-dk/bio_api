import typing
from enum import Enum
from typing import Optional
from pydantic import BaseModel



# Request classes

class NearestNeighborsRequest(BaseModel):
    """
    Parameters for a REST request for a nearest neighbors calculation.
    """
    # The filtering dict must exist, at there must at least be a filter on species
    input_mongo_id: str  # Required

    filtering: Optional[dict] = None
    cutoff: Optional[int] = None
    unknowns_are_diffs: Optional[bool] = None

class DistanceMatrixRequest(BaseModel):
    """
    Parameters for a REST request for a distance calculation.

    seq_collection: collection to find sequences in
    seqid_field_path: field path in dotted notation which contains the 'sequence id' the user wants to see
    profile_field_path: field path in dotted notation which contains the cgMLST allele profiles
    seq_mongo_ids: the  _id strings for the desired sequence documents
    """
    seq_mongo_ids: list | None


class HCTreeCalcRequest(BaseModel):
    """
    Parameters for a REST request for a tree calculation based on hierarchical clustering.
    Distances are taken directly from the request.
    """
    dmx_job: str
    # See https://docs.scipy.org/doc/scipy/reference/cluster.hierarchy.html
    method: typing.Literal["single", "complete", "average", "weighted", "centroid", "median", "ward"]


class SNPRequest(BaseModel):
    """
    Parameters for a REST request for a SNP calculation.

    seq_collection: collection to find sequences in
    seqid_field_path: field path in dotted notation which contains the 'sequence id' the user wants to see
    seq_mongo_ids: the  _id strings for the desired sequence documents
    reference_id: the _id string for the reference sequence
    depth: int = 15
    ignore_hz: bool
    """
    seq_mongo_ids: list
    reference_mongo_id: str
    depth: Optional[int] = None
    ignore_hz: Optional[bool] = None
    hpc_resources: Optional[dict] = None
    # TODO: hpc_resources: we probably need to be able to specify these in the request.


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
    distances: typing.Optional[dict] = None

class DistanceMatrixGETResponse(DistanceMatrixRequest, CommonGETResponse):
    result: typing.Any


class HCTreeCalcGETResponse(HCTreeCalcRequest, CommonGETResponse):
    result: typing.Optional[str]


class SNPGETResponse(SNPRequest, CommonGETResponse):
    result: typing.Optional[DistanceMatrixResult]