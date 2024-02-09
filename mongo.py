import re
from bson.objectid import ObjectId
from datetime import date
from pathlib import Path

import pymongo

#TODO Make this a configurable item somehow.
SEQUENCE_FIELD_MAPPING: dict = {
    'owner': 'categories.sample_info.summary.institution',
    'sequence_id': 'categories.sample_info.summary.sofi_sequence_id',
    'sample_id': 'name',
    'species': 'categories.species_detection.summary.detected_species',
    'allele_profile': 'categories.cgmlst.report',
    'sequence_type': 'categories.cgmlst.report.data.sequence_type',
    'fastq_path_pair': 'categories.paired_reads.summary.data',
}

def get_sequence_id(structure: dict):
    # TODO: use glom? https://github.com/mahmoud/glom
    return structure['categories']['sample_info']['summary']['sofi_sequence_id']


def get_alleles(structure: dict):
    # TODO: use glom? https://github.com/mahmoud/glom
    all_alleles:dict = structure['categories']['cgmlst']['report']['alleles']
    # Reduce the number of loci processed by cgmlst-dists to prevent it from running out of memory on laptop
    my_alleles = dict()
    for locus in all_alleles.keys():
        my_alleles[locus] = all_alleles[locus]
    return my_alleles

def profile_diffs(other_profile:dict, ref_profile, unknowns_are_diffs:bool=True):
    """Count the number of differences between two allele profiles."""
    diff_count = 0
    for locus in ref_profile.keys():
        try:
            ref_allele = int(ref_profile[locus])
        except ValueError:
            if unknowns_are_diffs:
                # Ref allele not intable - counting a difference.
                diff_count += 1
            # No reason to compare alleles if ref allele is not intable
            continue
        try:
            other_allele = int(other_profile[locus])
            if ref_allele != other_allele:
                # Both are intable but they are not equal - counting a difference.
                diff_count += 1
        except ValueError:
            if unknowns_are_diffs:
                # Other allele not intable - counting a difference.
                diff_count += 1
    return diff_count

class MongoAPIError(Exception):
    pass


class MongoAPI:
    def __init__(self,
        connection_string: str,
        sequence_field_mapping: dict=None,
    ):
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()
        self.sequence_field_mapping: dict = sequence_field_mapping or SEQUENCE_FIELD_MAPPING

    # Get samples from MongoDB object ids
    def get_samples(
        self,
        mongo_ids = None,
        species_name: str = None,
        fields: set = None
    ):

        if fields is None:
            fields = set(self.sequence_field_mapping.keys())

        pipeline = list()

        # Match
        match = dict()
        if mongo_ids:
            object_ids = [ObjectId(mongo_id) for mongo_id in mongo_ids]
            match['_id'] = { '$in': object_ids }
        species_field = self.sequence_field_mapping['species']
        if species_name:
            match[species_field ] = species_name

        pipeline.append(
            {'$match': match}
        )

        # Projection
        projection = dict()
        for field in fields:
            if isinstance(self.sequence_field_mapping[field], str):
                projection[field] = f"${self.sequence_field_mapping[field]}"
            else:
                projection[field] = self.sequence_field_mapping[field]

        pipeline.append(
            {'$project': projection
            }
        )

        return self.db.samples.aggregate(pipeline)


    def get_samples_from_sequence_ids(
        self,
        sequence_ids:list,
        fields: set = None
    ):

        if fields is None:
            fields = set(self.sequence_field_mapping.keys())
        pipeline = list()
        seqid_field = self.sequence_field_mapping['sequence_id']

        # Match
        pipeline.append(
            {'$match':
                {
                    seqid_field: {'$in': sequence_ids}
                }
            }
        )
        
        # Projection - map only the desired fields
        projection = dict()
        for field in fields:
            if isinstance(self.sequence_field_mapping[field], str):
                projection[field] = f"${self.sequence_field_mapping[field]}"
            else:
                projection[field] = self.sequence_field_mapping[field]
        
        pipeline.append(
            {'$project': projection
            }
        )

        return self.db.samples.aggregate(pipeline)

    def get_sequences(self, sequence_ids:list):
        # Get sequences from sequence ids
        list_length = len(sequence_ids)
        print(f"Looking up {list_length} sequences in MongoDB")
        sequence_id_field = self.sequence_field_mapping['sequence_id']
        print(f"Sequence ID field is {sequence_id_field}")
        query = {sequence_id_field: {'$in': sequence_ids}}
        print("Query:")
        print(query)
        sequences = self.db.samples.find(query)
        document_count = self.db.samples.count_documents(query)
        if list_length != document_count:
            print("ERROR: We did not find the correct number of sequences.")
            print("These are the sequence IDs that was looked up:")
            print(sequence_ids)
            print("These are the sample names we found:")
            for sequence in sequences:
                print(sequence['name'])
            raise MongoAPIError (f"You asked for {list_length} documents, but the number of matching documents is {document_count}.")
        return sequences
    
    def get_folder_from_sequence_id(self, sequence_id: str):
        sequences = list(self.get_samples_from_sequence_ids([sequence_id], fields=['fastq_path_pair']))
        assert len(sequences) == 1
        try:
            path_str = sequences[0]['fastq_path_pair'][0]
        except KeyError:
            print("Fastq paths not found - using dummy paths. This should not happen in production.")
            path_str = '/dummy/path/'
        path = Path(path_str)
        return str(path.parent)
    
    def get_metadata_from_isolate_ids(
        self,
        collection: str,
        isolate_ids: list,
        fields
    ):
        # Get metadata from isolate ids
        # Note: 'isolate' is the appropriate term here as metadata relate to isolates, not sequences
        list_length = len(isolate_ids)
        query = {'isolate_id': {'$in': isolate_ids}}
        document_count = self.db[collection].count_documents(query)
        fields_match = {'_id': 0, 'isolate_id': 1}
        for field in fields:
            fields_match[field] = 1
        mongo_cursor = self.db[collection].find(query, fields_match)
        if document_count > len(isolate_ids):  # document_count < list length is OK since not all isolates might have metadata!
            raise MongoAPIError (f"Too many documents: You asked for {list_length} documents, but the number of matching documents is {document_count}.")
        return document_count, mongo_cursor
    
    def get_metadata_from_sequence_ids(
            self,
            sequence_ids: list,
            bifrost_fields,
            tbr_collection: str=None,
            tbr_fields: str=None
        ):
        
        pipeline = list()
        seqid_field = self.sequence_field_mapping['sequence_id']

        # Match
        pipeline.append(
            {'$match':
                {
                    seqid_field: {'$in': sequence_ids}
                }
            }
        )

        if tbr_collection is not None:
            # Lookup data in metadata collection
            # Join field 'name' in samples collection with field 'isolate_id' in metadata collection
            pipeline.append(
                {
                    '$lookup': {
                        'from': tbr_collection,
                        'localField': 'name',
                        'foreignField': 'isolate_id',
                        'as': 'tbr'
                    },
                }
            )
            pipeline.append({'$unwind': '$tbr'})

        # Projection - map only the desired fields
        projection = dict()
        for field in bifrost_fields:
            if isinstance(self.sequence_field_mapping[field], str):
                projection[field] = f"${self.sequence_field_mapping[field]}"
            else:
                projection[field] = self.sequence_field_mapping[field]
        
        # projection['tbr'] = '$tbr'
        projection['_id'] = 0

        if tbr_collection is not None:
            for tbr_field in tbr_fields:
                projection[tbr_field] = f'$tbr.{tbr_field}'

        print("Projection:")
        print(projection)
        
        pipeline.append(
            {'$project': projection
            }
        )

        return self.db.samples.aggregate(pipeline)

    def find_all_jobs(self):
        return self.db.hpc_jobs.find()
    
    def find_unfinished_jobs(self):
        return self.db.hpc_jobs.find({'s': {'$ne': 'C'}})

    def find_jobs_from_job_id_list(self, job_ids: list):
        job_ids_str = [ str(job_id) for job_id in job_ids]
        return self.db.hpc_jobs.find({'job_id': {'$in': job_ids_str}})
    
    # Use get_samples_from_sequence_ids
    # def get_sample(self, sequence_id):
    #     sequence_id_field = self.sequence_field_mapping['sequence_id']
    #     return self.db.samples.find_one({sequence_id_field: sequence_id})
    
    def get_allele_profiles_for_species(self, species_name: str):
        species_field = self.sequence_field_mapping['species']
        allele_profile_field = self.sequence_field_mapping['allele_profile']
        return self.db.samples.find({species_field: species_name}, {allele_profile_field: 1})
    
    def get_nearest_neighbors(
            self,
            sequence_id:str,
            cutoff:int,
            unknowns_are_diffs: bool
        ):
        reference_sequence = next(self.get_samples_from_sequence_ids([sequence_id],
            fields=['sequence_id', 'species', 'allele_profile']))
        print(f"Finding nearest neighbors for sequence with sequence ID {sequence_id}")
        print(f"Cutoff is {str(cutoff)}")
        species = reference_sequence['species']
        print(f"Species: {species}")
        number_of_allele_profiles = self.db.samples.count_documents({self.sequence_field_mapping['species']: species, self.sequence_field_mapping['allele_profile']: {"$exists":True}})
        print(f"Number of profiles found: {str(number_of_allele_profiles)}")
        
        pipeline = list()
        pipeline.append(
            {'$match':
                {
                    self.sequence_field_mapping['species']: species,
                    self.sequence_field_mapping['allele_profile']: {'$exists': True},
                    self.sequence_field_mapping['sequence_id']: {'$exists': True}
                }
            }
        )
        pipeline.append(
            {'$project':
                {
                    'sequence_id': f"${self.sequence_field_mapping['sequence_id']}",
                    'allele_profile': f"${self.sequence_field_mapping['allele_profile']}",
                }
            }
        )
        sequences_to_compare_with = self.db.samples.aggregate(pipeline)
        nearest_neighbors = list()
        for other_sequence in sequences_to_compare_with:
            if other_sequence['sequence_id'] == reference_sequence['sequence_id']:
                print("Ignoring reference sequence.")
            else:
                diff_count = profile_diffs(other_sequence['allele_profile']['alleles'], reference_sequence['allele_profile']['alleles'], unknowns_are_diffs)
                if diff_count <= cutoff:
                    nearest_neighbors.append({'sequence_id': other_sequence['sequence_id'], 'diff_count': diff_count})
        return sorted(nearest_neighbors, key=lambda x : x['diff_count'])