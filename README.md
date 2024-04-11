# About this document
The main purpose of the README is to deliver a prosaic description of the input and output fields of Bio API. Please also see the OpenAPI (Swagger) specification the Bio API exhibits at <bio_api_url>/docs.

In most cases, nested MongoDB fields can be specified using dotted notation (like "my.nested.mongodb.field").

In general "mongo ids" in this document means strings that MongoDB can turn into ObjectID values.

# General principles of Bio API
At least for now, all operations in Bio API concern initialization of calculations and retrieving the results of these. Currently, all calculations are done inside Bio API, though it is planned that in later versions Bio API should also be able to control calculations in an HPC environment.

# Data storage
Bio API is built for using MongoDB as the primary data storage (although it would be possible to adapt the code to other database backends or even using another API for data storage).

Bio API assumes that all relevant sequence data reside in MongoDB documents (and it never changes these documents in any way). However, it does not make any assumptions concerning collection names and field names for sequence data. Thus, it is up to the client code to 'know' the structure of the sequence documents.

Bio API stores its own data in collections with hard-coded names.

Generally, everything concerning a particular calculation is stored in a MongoDB document - both input parameters, calculation metadata, and calculation results. However, distance matrices are actually stored in a filesystem. This is because distance matrices tend to grow very large and outgrow the maximum size of a MongoDB document. That means that one should remember to reserve a relatively large filesystem storage area for distance matrices and keep an eye of the amount of free disk space. The location of the filesystem for distance matrices is set via the environment variable DMX_DIR.

## General structuring principles for API requests and responses
All requests and responses are JSON-formatted.

### Use of POST and GET requests
Initializing calculations its done in POST requests, and getting calculation status and results is done in GET requests.

### POST request structure
The structure of the POST requests for the different calculation types are described in paragraphs below for each individual calculation type.

### Responses to POST requests
For now, the responses to all successful POST requests are structured in the same way and consist of just these three fields:

- job_id: the stringified version of the MongoDB ObjectID of the document that contains the calculation object
- created_at: a string containing an ISO timestamp for when the object was created
- status: this will in fact always be 'init' when the object is just created. Other possible statuses are 'error' and 'completed'.

Of course, some error scenarios are also possible. These will result in a response with a suitable HTTP status code and a message body containing just a "detail" field with details of the error.

### GET requests and responses
To get the status and possibly the result of calculation you send its job_id in a GET request. This means that the client application must have somehow remembered this id when it was sent back to the client with the POST response. Without the job_id you cannot get a result back from Bio API.

Per default, the GET request will result in a response which contains everything that is stored in the calculation object, which means:
- All input parameters
- All status/meta information (these fields are the same as in the POST response plus a 'finished_at' field if the calculation is finished)
- The full result, which will always be located in a root level field named 'result' (but the structure of the fields' content will vary depending on the calculation type).

However, the GET request takes a 'level' parameter which defaults to 'full', and if this parameter is set to anything else than 'full' (for instance 'status'), the actual result will not be sent with the response. This is handy if you just want to check the status of a long-running job so as to avoid the request-response cycle to hang for at long time, possibly leading to a timeout.

# Nearest Neighbors, distance matrices, and trees
This functionality implements generating trees in Newick file format from cgMLST allele profiles. The allele profiles must exist in a MongoDB database in a certain field (possibly a nested field) on the sequence documents.

The typical workflow is here that you start by defining af group of sequences that you want to look at using Nearest Neighbors. Then, with the mongo ids of those sequences as input, you first generate a distance matrix (which is an intermediate result that is stored separately), and then you generate a tree from that distance matrix, choosing a particular tree-generation method.

## Nearest Neighbors
Nearest neighbors is a comparison algorithm that compares the allele profile of one sequence with a (typically large) set of other allele profiles. It counts the number of allelic differences between the profiles. If a certain profile has a difference count that is smaller than a cutoff value the profiles' mongo ID is reported back to the client.

### POST request input fields
- seq_collection: the MongoDB collection that contains the sequences
- filtering: a dictionary in the format {"field_1": "value_1", "field_2": "value_2"} for filtering the sequences
- profile_field_path: field (or dotted field path) for where Bio API should look for the cgMLST allele profiles to compare
- input_mongo_id: mongo id for the reference profile that has to be compared to others
- cutoff: integer value indicating the maximum allelic distance (maximum number of differences) between the input profile and the compared profile
- unknowns_are_diffs: Boolean value that indicates whether an unknown value in an allele profile should count as 'different' or 'equal'

### GET request output structure
Nearest Neighbors will output its result as a list of {"id": "string", "diff_count": 0} elements where id is a stringified mongo id of a sequence and diff_count is the number of differences. The list will be sorted with the sequence with the smallest difference first.

## Distance matrices
The main input for generating a distance matrix is a list of mongo ids for the sequences which must be compared. The output is in essence a classic distance matrix with the same ID's on both axis; however, the format is adapted to fit within the JSON standard.

### POST request input fields
- seq_collection: name of the MongoDB collection where the sequences exist
- seqid_field_path: field (or dotted field path) of the 'sequence ID' field that the user wants to see
- profile_field_path: field (or dotted field path) that holds the allele profile
- seq_mongo_ids: mongo ids of the input sequences

### GET request output structure
The "result" field contains a dictionary of dictionaries containing the 'sequence IDs' as keys in both the inner and outer dictionaries, and the distance between each individual sequence pair as value.

## Trees
A tree represents the distances between the elements in the distance matrix in a hierarchical way, using a particular tree generation method. The tree is formatted in Newick format. It can be relevant to produce more trees from the same distance matrix using different tree generation methods as the methods produce (of course) slightly different trees.

### POST request input fields
- dmx_job: the job_id of the distance matrix calculation to use
- method: a tree calculation method. Allowed methods are 'single', 'complete', and probably others (this has to be investigated).

### GET request output structure
The result of the tree generation calculation is the generated tree in Newick format.