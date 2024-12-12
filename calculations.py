import datetime
from os import getenv
from pathlib import Path
from json import dump, load
import asyncio
from io import StringIO
import abc

import pymongo
from bson.objectid import ObjectId
from pandas import DataFrame, read_table, read_csv
from tree_maker import make_tree

DMX_DIR = getenv('DMX_DIR', '/dmx_data')


class MissingDataException(Exception):
    pass


def hoist(var, dotted_field_path:str):
    """
    'Hoists' a value from a nested dictionary using a dotted field path.
    
    Example:
        var = {'my': {'nested': {'dictionary': 123}}}
        dotted_field_path = 'my.nested.dictionary'
        print(hoist(var, dotted_field_path)) -> The above example should return 123.
    
    Args:
        var (dict): The nested dictionary.
        dotted_field_path (str): A string representing the path to the desired value.
    
    Returns:
        The value at the specified path.
    """

    for path_element in dotted_field_path.split('.'):
        # Split the dotted path into segments (e.g., "my.nested.dictionary" -> ["my", "nested", "dictionary"])
        var = var[path_element]
    
    # Return the final value located at the end of the path
    return var

def strs2ObjectIds(id_strings: list):
    """
    Converts a list of strings to a set of ObjectIds
    """
    output = list()
    for id_str in id_strings:
        output.append(ObjectId(id_str))
    return output


class MongoAPI:
    """
    A helper class for interacting with MongoDB.
    
    This class provides methods for querying MongoDB collections with support for filters 
    and retrieving specific fields.
    """
    def __init__(self,
        connection_string: str,
    ):
        """
        Initialize the MongoAPI instance with a MongoDB connection string.
        
        Args:
            connection_string (str): MongoDB connection string.
        """
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()

    async def get_field_data(
            self,
            collection:str,
            mongo_ids:list | None,
            field_paths:list,
        ):
        """
        Retrieves specific fields from a MongoDB collection.

        Args:
            collection (str): Name of the MongoDB collection.
            mongo_ids (list | None): List of MongoDB ObjectIds as strings to filter documents.
            field_paths (list): List of field paths to retrieve (in dotted notation) ['some.example.field1', 'some.other.example.field2']

        Returns:
            tuple: (Number of matching documents, Cursor to the documents).
        """
        if mongo_ids: #if document IDs exist
            # Create a filter to match documents by a list of ObjectIds
            filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}

            #number of documents that match the filter
            document_count = self.db[collection].count_documents(filter) 

            #Retrieve a cursor (pointer or iterator used to traverse query results) to the filtered documents with only the specified fields
            cursor = self.db[collection].find(filter, {field_path: True for field_path in field_paths})
            #for document in cursor:
            #    print(document['name'])
        else:
            # no filter
            document_count = self.db[collection].count_documents({})
            cursor = self.db[collection].find({}, {field_path: True for field_path in field_paths})
        return document_count, cursor

# Fetch the MongoDB connection string from an environment variable to create an instance of MongoAPI to interact with the database
connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
mongo_api = MongoAPI(connection_string)

class Calculation(metaclass=abc.ABCMeta):
    """
    Abstract base class for defining calculations.
    
    This class provides a structure for performing computations and persisting their state in MongoDB.
    """
    created_at: datetime.datetime | None # Timestamp for when the calculation was created
    finished_at: datetime.datetime | None
    status: str
    result: str | None = None

    def __init__(
        self,
        status: str = 'init',
        created_at: datetime.datetime | None = None,
        finished_at: datetime.datetime | None = None,
        _id: ObjectId | None = None,
        result = None
        ):
        """
        Initializes a Calculation instance.
        
        Args:
            status (str): Current status of the calculation.
            created_at (datetime | None): Timestamp for when the calculation was created.
            finished_at (datetime | None): Timestamp for when the calculation was completed.
            _id (ObjectId | None): MongoDB document ID for this calculation.
            result: Result of the calculation.
        """
        self.status = status
        self.created_at = created_at if created_at else datetime.datetime.now(tz=datetime.timezone.utc)
        self.finished_at = finished_at
        self._id = _id
        self.result = result
    
    def to_dict(self):
        """
        Converts the calculation instance into a dictionary for storage.
        
        Returns:
            dict: Dictionary representation of the instance.
        """
        content = dict() # Empty dictionary to hold the calculation instance attributes
        for key, value in vars(self).items():
            if isinstance(value, datetime.datetime):
                content[key] = value.isoformat() # Convert datetime attributes to ISO format
            elif key == '_id':
                content['job_id'] = str(value) # Rename '_id' to 'job_id' for easier reference
            else:
                content[key] = value # add attributes
        return content
    
    # https://stackoverflow.com/questions/2736255/abstract-attributes-in-python
    @property
    @abc.abstractmethod
    def collection(self):
        """
        Abstract property to define the MongoDB collection associated with the calculation.
        """
        return 'my_collection'
    
    async def insert_document(self, **attrs):
        """
        Inserts a new document into the MongoDB collection.

        Args:
            **attrs: Additional attributes to store in the document.

        Returns:
            ObjectId: The ID of the newly inserted document.
        """
        global_attrs = {
            'status': self.status,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
            'result': self.result
            }
        doc_to_save = dict(global_attrs, **attrs) # Merge global attributes with any additional attributes passed

        # insert document to mongoDB and acknowlegde it was succesful
        mongo_save = mongo_api.db[self.collection].insert_one(doc_to_save)
        assert mongo_save.acknowledged == True 

        # add an ID for the document to the instance and return it
        self._id = mongo_save.inserted_id
        return self._id
    
    @classmethod
    def find(cls, id: str):
        """
        Retrieves a calculation instance based on its MongoDB document ID.
        """

        doc = mongo_api.db[cls.collection].find_one({'_id': ObjectId(id)})
        if doc is None:
            return None
        return cls(**doc)
    
    async def get_field(self, field):
        """
        Retrieves a specific field (str) from the MongoDB document.
        """

        doc = mongo_api.db[self.collection].find_one({'_id': self._id}, {field: True})
        return doc[field]
    
    async def get_result(self):
        """
        Retrieves the result of the calculation.
        """
        return await self.get_field('result')

    async def store_result(self, result, status:str='completed'):
        """
        Update the MongoDB document that corresponds with the class instance with its result and inserts 
        a timestamp for when the calculation was completed and mark the calculation as completed

        Args:
            result: The result of the calculation.
            status (str): The status to set (default is 'completed').
        """

        # TODO maybe merge with update?
        print("Store result.")
        print(f"My collection: {self.collection}")
        print("My _id:")
        print(self._id)
        update_result = mongo_api.db[self.collection].update_one(
            {'_id': self._id}, {'$set': {
                'result': result,
                'finished_at': datetime.datetime.now(tz=datetime.timezone.utc),
                'status': status
                }
            }
        )
        assert update_result.acknowledged == True

    async def update(self):
        """
        Update the MongoDB document that corresponds with the calculation class instance.
        """
        print("Update.")
        print(f"My collection: {self.collection}")
        print("My _id:")
        print(self._id)
        print("__dict__:")
        print(self.__dict__)
        update_result = mongo_api.db[self.collection].update_one(
            {'_id': self._id}, {'$set': {
                    **vars(self)
                }
            }
        )
        assert update_result.acknowledged == True

    @abc.abstractmethod
    async def calculate(self, cursor):
        """
        Abstract method for performing the calculation. 
        Must be implemented in subclasses.

        Args:
            cursor: MongoDB cursor to the data needed for the calculation.
        """
        pass

class NearestNeighbors(Calculation):
    """
    This class is a subclass of `Calculation`. It inherits the functionality of `Calculation` but customizes the behavior
    to perform a nearest-neighbor calculation by comparing allele profiles of sequences in a MongoDB collection.

    Aim: find sequences that have a similar allele profile to a specified input sequence. The class allows for 
    filtering the sequences based on specific criteria (e.g., species) and calculates the number of differences (or 
    "distance") between the input sequence and other sequences in the collection. If the difference is below a specified
    cutoff, the sequence is considered a "nearest neighbor."

    Key attributes:
        seq_collection (str): The MongoDB collection containing the sequences to compare.
        filtering (dict): Filters to apply to the sequences before performing the nearest-neighbor search (e.g., species, other attributes).
        profile_field_path (str): The field path for the allele profile in the sequence documents in mongoDB.
        input_mongo_id (str): The MongoDB ID of the input sequence that is being compared against others.
        cutoff (int): The maximum allowable difference to consider a sequence as a nearest neighbor.
        unknowns_are_diffs (bool): If True, unknown alleles are treated as differences during the comparison.
        input_sequence (dict | None): The input sequence document itself.

    Methods:
        insert_document: Inserts the calculation details into the database.
        query_mongodb_for_input_profile: Queries the MongoDB collection to retrieve the input sequence's allele profile.
        profile_diffs: Compares two allele profiles and returns the number of differences.
        calculate: Performs the nearest-neighbor calculation and stores the results.
        to_dict: Converts the object to a dictionary, including the calculated nearest neighbors.
    """

    collection = 'nearest_neighbors'

    # attributes
    seq_collection: str
    filtering: dict = dict()
    profile_field_path: str
    input_mongo_id: str
    cutoff: int
    unknowns_are_diffs: bool = True
    input_sequence: dict | None

    @property
    def input_profile(self):
        return hoist(self.input_sequence, self.profile_field_path)

    def __init__(
            self,
            seq_collection: str | None = None,
            filtering: dict | None = None,
            profile_field_path: str | None = None,
            input_mongo_id: str | None = None,
            cutoff: int | None=None,
            unknowns_are_diffs: bool = True,
            **kwargs):
        """
        Initializes the NearestNeighbors calculation with parameters for MongoDB collection, filtering, profile field, 
        cutoff, and whether unknown alleles should be considered as differences. Inherits initialization from the 
        `Calculation` superclass.
        """
        super().__init__(**kwargs)
        self.seq_collection = seq_collection
        self.filtering = filtering
        self.profile_field_path = profile_field_path
        self.input_mongo_id = input_mongo_id
        self.unknowns_are_diffs = unknowns_are_diffs
        self.cutoff = cutoff
    
    async def insert_document(self):
        """
        Inherited from `Calculation`. This method inserts the document into the MongoDB database, adding fields related 
        to the nearest-neighbor calculation, such as `seq_collection`, `profile_field_path`, and `cutoff`.
        """
        await super().insert_document(
            seq_collection=self.seq_collection,
            profile_field_path=self.profile_field_path,
            filtering=self.filtering,
            input_mongo_id=self.input_mongo_id,
            cutoff=self.cutoff,
            unknowns_are_diffs = self.unknowns_are_diffs,
            # self.input_sequence is intentionally not stored as it is already stored in the sequence document
        )
        return self._id

    async def query_mongodb_for_input_profile(self):
        """
        Queries MongoDB to fetch the allele profile for the input sequence based on its MongoDB ID.
        If no profile is found, raises a `MissingDataException`.
        """
        profile_count, cursor = await mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.profile_field_path],
            mongo_ids=[self.input_mongo_id]
            )
        if profile_count == 0:
            message = f"Could not find a document with id {self.input_mongo_id} in collection {self.seq_collection}."
            raise MissingDataException(message)
        reference_profile = next(cursor)
        return reference_profile
    
    def profile_diffs(self, other_profile:dict):
        """
        Counts the number of differences between allele profile of the input sequence to another.
        If allele is unknown (cannot be converted to an integer), the difference `unknowns_are_diffs` is True.
        """
        diff_count = 0
        for locus in self.input_profile.keys():
            try:
                ref_allele = int(self.input_profile[locus])
            except ValueError:
                if self.unknowns_are_diffs:
                    # Ref allele not integer-convertible - counting a difference.
                    diff_count += 1
                # No reason to compare alleles if ref allele is not integer-convertible
                continue
            try:
                other_allele = int(other_profile[locus])
                if ref_allele != other_allele:
                    # Both are integer-convertible but they are not equal - counting a difference.
                    diff_count += 1
            except ValueError:
                if self.unknowns_are_diffs:
                    # Other allele not integer-convertible - counting as difference.
                    diff_count += 1
        return diff_count
    
    async def calculate(self):
        """
        Performs the nearest-neighbor calculation by comparing the input sequence to all other sequences in the MongoDB 
        collection. Only sequences that meet the filtering criteria and have an allele profile are considered. For each 
        sequence, the number of differences from the input sequence is calculated. Sequences with differences less than or 
        equal to the cutoff value are considered nearest neighbors.
        
        Inherits the database querying functionality from the `Calculation` class and uses the `store_result` method to 
        save the results.
        """
        print(f"Sequence collection: {self.seq_collection}")
        print(f"Profile field path: {self.profile_field_path}")

        # Get the count of sequences in the collection that have a profile field
        comparable_sequences_count = mongo_api.db[self.seq_collection].count_documents({self.profile_field_path: {"$exists":True}})
        print(f"Comparable sequences found: {str(comparable_sequences_count)}")

        # Initialize the MongoDB aggregation pipeline to filter and project data
        pipeline = list()

        print("Filters to apply to sequences before running nearest neighbors:")
        # There must always be a filter on species as different species have different cgMLST schemas
        try:
            # Apply any filtering criteria passed to the instance (e.g., species filters)
            for k, v in self.filtering.items():
                print(f"{k} must be {v}")
                pipeline.append(
                {'$match':
                    {
                        k: {'$eq': v},
                    }
                }
            )
        except KeyError as e:
            await self.store_result(str(e), 'error')

        # Add additional filter to include only sequences that have the profile field
        pipeline.append(
            {'$match':
                {
                    self.profile_field_path: {'$exists': True},
                }
            }
        )

        # Project only the profile field for each sequence # QA is this for querying
        pipeline.append(
            {'$project':
                {
                    self.profile_field_path: 1,
                }
            }
        )

        # Execute the aggregation pipeline to get sequences to compare with #QA is this also for querying, exactly what is the aggregation pipeline
        sequences_to_compare_with = mongo_api.db[self.seq_collection].aggregate(pipeline)

        nearest_neighbors = list()
        # Loop through each sequence to compare its profile with the input sequence
        for other_sequence in sequences_to_compare_with:
            if not other_sequence['_id'] == self.input_sequence['_id']:
                # Calculate the number of differences between the input sequence and the other sequence
                diff_count = self.profile_diffs(hoist(other_sequence, self.profile_field_path))
                # If the difference count is within the cutoff, consider this sequence as a nearest neighbor
                if diff_count <= self.cutoff:
                    nearest_neighbors.append({'_id': other_sequence['_id'], 'diff_count': diff_count})
        
        # Sort the nearest neighbors by the number of differences (ascending order)
        self.result = sorted(nearest_neighbors, key=lambda x : x['diff_count'])

        await self.store_result(self.result)
    
    def to_dict(self):
        """
        Converts the class instance with result to a dictionary representation. Modifies the result list 
        by adding 'id' for each nearest neighbor and removing the '_id' field from each result.
        
        Inherited behavior from `Calculation` is extended to include the result transformation.
        """

        # Get the dictionary representation of the object from the superclass
        content = super().to_dict()

        # Check if 'result' is present and is a list of nearest neighbors
        if 'result' in content and type(content['result']) is list:
            # Loop through the result list and format each neighbor entry
            r: dict
            for r in content['result']:
                #Add 'id' field (converted from '_id') for easier usage
                r['id'] = str(r['_id'])
                # Remove the '_id' field from the result to clean up the data
                r.pop('_id')

        # updated dictionary with cleaned data
        return content

class DistanceCalculation(Calculation):
    """
    This class is a subclass of `Calculation`. It inherits the functionality of `Calculation` but customizes the behavior
    to perform a distance matrix calculation by comparing allele profiles of sequences in a MongoDB collection.

    Aim: calculate a distance matrix between sequences based on their allele profiles. The class first retrieves the allele 
    profiles of sequences from a MongoDB collection, then generates an allele matrix. Using this matrix, it computes a 
    distance matrix using the external `cgmlst-dists` tool. 
    The distance matrix is then stored as a CSV file and allele matrix dataframe as TSV file.
    The class also stores the sequence IDs and their associated MongoDB IDs for reference.

    Key attributes:
        seq_collection (str): The MongoDB collection containing the sequences for comparison.
        seqid_field_path (str): The field path for the sequence IDs in the MongoDB documents.
        profile_field_path (str): The field path for the allele profiles in the MongoDB documents.
        seq_mongo_ids (list | None): A list of MongoDB sequence IDs to include in the calculation (optional).
    
    Methods:
        insert_document: Inserts the calculation details into the database and creates a folder for storing the results.
        query_mongodb_for_allele_profiles: Queries the MongoDB collection to retrieve the allele profiles for the specified sequences.
        _amx_df_from_mongodb_cursor: Generates an allele matrix DataFrame from the MongoDB cursor containing allele profiles.
        _save_amx_df_as_tsv: Saves the allele matrix DataFrame as a TSV file for documentation.
        _dmx_df_from_amx_tsv: Generates a distance matrix DataFrame from the allele matrix TSV file using the `cgmlst-dists` tool.
        calculate: Performs the distance matrix calculation, generates and saves the allele and distance matrices, and stores the results.
        to_dict: Converts the object to a dictionary, including the results and sequence-to-MongoDB ID mapping.
    """
    collection = 'dist_calculations'

    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    seq_mongo_ids: list | None

    def __init__(
            self,
            seq_collection: str | None=None,
            seqid_field_path: str | None = None,
            profile_field_path: str | None = None,
            seq_mongo_ids: list | None = None,
            **kwargs):
        """
        Initializes the DistanceCalculation instance with the necessary parameters (see above).
        """
        super().__init__(**kwargs) # Call the parent class's constructor
        self.seq_collection = seq_collection
        self.seqid_field_path = seqid_field_path
        self.profile_field_path = profile_field_path
        self.seq_mongo_ids = seq_mongo_ids
    
    async def insert_document(self):
        """
        Insert the document into the database for this calculation, creating a folder for storing results.
        """
        await super().insert_document(
            seq_collection=self.seq_collection,
            seqid_field_path=self.seqid_field_path,
            profile_field_path=self.profile_field_path,
            seq_mongo_ids=self.seq_mongo_ids,
        )
        Path(self.folder).mkdir()
        return self._id
    
    @property
    def folder(self):
        """ Return the folder corresponding to the class instance """
        return Path(DMX_DIR, self.to_dict()['job_id'])

    @property
    def allele_mx_filepath(self):
        "Return the filepath for the allele matrix file corresponding with the class instance"
        return str(Path(self.folder, 'allele_matrix.tsv'))
    
    @classmethod
    def get_dist_mx_filename(cls):
        return 'distance_matrix.csv'

    @property
    def dist_mx_filepath(self):
        "Return the filepath for the distance matrix file corresponding with the class instance"
        return str(Path(self.folder, self.get_dist_mx_filename()))

    async def query_mongodb_for_allele_profiles(self):
        """
        Query MongoDB for the allele profiles of the sequences specified by `seq_mongo_ids`.

        Raises:
            MissingDataException: If the requested sequences cannot be found or if the number of profiles doesn't match the requested sequences.
        
        Returns:
            profile_count (int): The number of profiles found in MongoDB.
            cursor (Cursor): The MongoDB cursor for the profile data.
        """
        profile_count, cursor = await mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.seqid_field_path, self.profile_field_path],
            mongo_ids=self.seq_mongo_ids
            )
        if self.seq_mongo_ids is not None and len(self.seq_mongo_ids) != profile_count:
            message = "Could not find the requested number of sequences. " + \
                f"Requested: {str(len(self.seq_mongo_ids))}, found: {str(profile_count)}"
            raise MissingDataException(message)
        return profile_count, cursor

    async def _amx_df_from_mongodb_cursor(self, cursor):
        """
        Generate an allele matrix as a DataFrame from the MongoDB cursor containing allele profiles.

        Also generates a dictionary for tracing sequence IDs back to mongo IDs.

        Args:
            cursor (Cursor): The MongoDB cursor containing allele profile data.
        
        Returns:
            df (DataFrame): The allele matrix as a DataFrame.
            mongo_ids (dict): A dictionary mapping sequence IDs to MongoDB IDs.
        """
        full_dict = dict() # Store allele profiles
        mongo_ids = dict() # Map sequence IDs to MongoDB IDs

        try:
            while True:
                mongo_item = next(cursor)
                try:
                    sequence_id = hoist(mongo_item, self.seqid_field_path)
                except KeyError:
                    raise MissingDataException(f"Sequence document with id {str(mongo_item['_id'])} does not contain sequence id field path '{self.seqid_field_path}'.")
                try:
                    allele_profile = hoist(mongo_item, self.profile_field_path)
                    full_dict[sequence_id] = allele_profile
                    mongo_ids[sequence_id] = mongo_item['_id']
                except KeyError:
                    raise MissingDataException(f"Sequence document with id {str(mongo_item['_id'])} does not contain profile field path '{self.profile_field_path}'.")
        except StopIteration:
            pass

        # Convert the dictionary of allele profiles into a DataFrame
        df = DataFrame.from_dict(full_dict, 'index', dtype=str)
        return df, mongo_ids

    async def _save_amx_df_as_tsv(self, allele_mx_df):
        "Save allele matrix dataframe as TSV file"
        with open(self.allele_mx_filepath, 'w') as allele_mx_file_obj:
            allele_mx_file_obj.write("ID")  # Without an initial string in first line cgmlst-dists will fail!
            allele_mx_df.to_csv(allele_mx_file_obj, index = True, header=True, sep ="\t")

    async def _dmx_df_from_amx_tsv(self):
        """
        Generate a distance matrix DataFrame from the allele matrix TSV file.

        Uses the external `cgmlst-dists` tool to compute the distance matrix from the allele matrix.

        Raises:
            OSError: If the external tool `cgmlst-dists` fails to execute.

        Returns:
            df (DataFrame): The computed distance matrix.
        """
        sp = await asyncio.create_subprocess_shell(f"cgmlst-dists {self.allele_mx_filepath}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await sp.communicate()

        await sp.wait()
        if sp.returncode != 0:
            errmsg = (f"Could not run cgmlst-dists on {self.allele_mx_filepath}!")
            raise OSError(errmsg + "\n\n" + stderr.decode('utf-8'))

        # Read the output of cgmlst-dists into a DataFrame
        df = read_table(StringIO(stdout.decode('utf-8')))
        df.rename(columns = {"cgmlst-dists": "ids"}, inplace = True)
        df = df.set_index('ids')
        return df

    async def calculate(self, cursor):
        """
        Perform the distance matrix calculation by processing allele profiles and generating the matrix.

        This method:
        - Retrieves the allele matrix from MongoDB.
        - Saves it as a TSV file.
        - Generates the distance matrix from the allele matrix.
        - Saves the distance matrix as a CSV file.
        - Stores the sequence-to-MongoDB ID mapping result.

        Args:
            cursor (Cursor): The MongoDB cursor for the allele profiles to be processed.
        """
        try:
            allele_mx_df, mongo_ids_dict = await self._amx_df_from_mongodb_cursor(cursor)
            await self._save_amx_df_as_tsv(allele_mx_df)  # The allele mx is only saved as documentation
            dist_mx_df: DataFrame = await self._dmx_df_from_amx_tsv()
            dist_mx_df.to_csv(path_or_buf=self.dist_mx_filepath)

            # We do not store the distance matrix in MongoDB because it might grow to more than 16 MB.
            # Instead we just store a dictionary of sequence IDs and their related mongo IDs.
            await self.store_result({'seq_to_mongo': mongo_ids_dict})
            print("Distance matrix calculation is finished!")
        except MissingDataException as e:
            # store error under the key 'result' within the mongoDB
            await self.store_result(str(e), 'error')


class TreeCalculation(Calculation):
    """
    This class is a subclass of `Calculation` that generates a phylogenetic tree based on a precomputed distance matrix.
    
    The `TreeCalculation` class takes the results from a previous distance matrix calculation and applies a tree-building
    algorithm (see which tree types you can make) to create a phylogenetic tree in Newick format.

    Attributes:
        dmx_job (str): The job ID of the distance matrix calculation.
        method (str): The tree-building algorithm to use (e.g., 'neighbor_joining', 'UPGMA').
        collection (str): The MongoDB collection where tree calculations are stored.
    
    Methods:
        insert_document: Inserts the tree calculation details into the database.
        calculate: Loads the distance matrix, creates the tree, and stores the result.
    """
    dmx_job: str
    method: str
    collection = 'tree_calculations'

    def __init__(self, dmx_job:str | None = None, method:str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.dmx_job = dmx_job
        self.method = method
    
    async def insert_document(self):
        """
        Inserts the TreeCalculation details into the database. This includes the job ID and the selected method.
        """
        await super().insert_document(
            dmx_job=self.dmx_job,
            method=self.method
        )
        # document id
        return self._id

    async def calculate(self):
        """
        Loads the precomputed distance matrix, applies the tree-building method, and stores the result.
        
        This method retrieves the distance matrix from a `DistanceCalculation` instance, constructs a tree using 
        the specified method, and stores the Newick format tree as the result.
        """
        dc = DistanceCalculation.find(self.dmx_job)
        try:
            dist_df: DataFrame = read_csv(Path(dc.folder, DistanceCalculation.get_dist_mx_filename()), index_col=0)
            tree = make_tree(dist_df, self.method)
            print("Newick:")
            print(tree)
            await self.store_result(tree)
        except ValueError as e:
            await self.store_result(str(e), 'error')

    """

    FGL mentions there might be several places where there could be errors, so perhaps we should add some more details for errors and consider when there is missing data, values etc
    except FileNotFoundError as e:
        # Handle the case where the distance matrix file is not found
        await self.store_result(f"Distance matrix file not found: {str(e)}", 'error')
        
    except ValueError as e:
        # Handle other errors, possibly related to the tree-building process
        await self.store_result(f"Error in tree calculation: {str(e)}", 'error')
        
    except Exception as e:
        # Catch any unforeseen errors and log them
        await self.store_result(f"Unexpected error: {str(e)}", 'error')
    """

