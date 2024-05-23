# Documentation for Bio API test client

## Command-line scripts

The scripts are intended for testing and demo purposes only.

All scripts take an optional --noverify argument. If this is provided the script will skip checking SSL certificate validity.

### Environment variables

These environment variables need to be set in order to use the commands:

- MICROREACT_BASE_URL: Base URL where Microreact is available
- MICROREACT_ACCESS_TOKEN: Personal access token for a Microreact user

### get_project_json.py

This script will print all information stored in MongoDB for an existing Microreact project owned by the Microreact user given by MICROREACT_ACCESS_TOKEN. It will NOT fetch any actual data values (like sequence ID's, metadata content, etc.) since Microreact
stores these on a filesystem that normally is unavailable for users. The information that get_project will fetch is data about the project structure and graphical layout.

usage:

    python get_project_json.py <project_id> <--noverify>

*project_id*: The unique ID which defines the project

Only projects that are owned by the Microreact user who owns MICROREACT_ACCESS_TOKEN can be fetched.

### new_project_from_files.py

This script will create a new project that will be owned by the user given by MICROREACT_ACCESS_TOKEN. The project will we a minimal project and will only contain a tree.

Usage:

    python new_project_from_files.py <tree> <metadata>

*tree*:  Path to a Newick file containing a tree to add
*metadata*: Path to a .tsv file containing data that will be shown in Microreacts data table (first column should contain the IDs)

### new_project_from_mongo.py

This script will create a new project that will be owned by the user given by MICROREACT_ACCESS_TOKEN. The project will we a minimal project and will only contain
one or more trees.

Apart from the environment variables mentioned above, this script will also try to read the environment variable BIO_API_MONGO_CONNECTION.
This variable will be used as an URL for a MongoDB instance containing a tree calculation (created with Bio API). This MongoDB instance does not need
to be the same as the  one that exists in context with the Microreact instance.
If BIO_API_MONGO_CONNECTION is not set, the value will default to 'mongodb://mongodb:27017/bio_api_test'.

Usage:

    python new_project_from_mongo.py <trees> [--project_name <project_name>]

*trees*: Mongo ID(s) for document(s) in the 'tree_calculation' collection in the MongoDB instance given by BIO_API_MONGO_CONNECTION. If more than one tree, separate the ID swith commas without spaces. If argument is omitted, a random document from the tree_calculations collection will be chosen.

*project_name*:  A name to use for the project created in Microreact

### add_tree

This script will add another tree to an existing project owned by the user given by MICROREACT_ACCESS_TOKEN.

Usage:

    python add_tree.py <project_id> <newick_file>

*project_id*: The unique ID that defines the project in Microreact
*newick_file*:  Path to a Newick file containing the tree to add
