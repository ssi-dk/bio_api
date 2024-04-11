# About this document

The main purpose of the README is to deliver a prosaic description of the input and output fields of Bio API. Please also see the ApenAPI specification the Bio API exhibits at <bio_api_url>/docs.

In most cases, nested MongoDB fields can be specified using dotted notation (like "my.nested.mongodb.field").

In general "mongo ids" in this document means strings that MongoDB can turn into ObjectID values.

# Nearest Neighbors, distance matrices, and trees

This functionality implements generating trees in Newick file format from cgMLST allele profiles. The allele profiles must exist in a MongoDB database in a certain field (possibly a nested field) on the sequence documents.

## Nearest neighbors

Nearest neighbors is a comparison algorithm that compares the allele profile of one sequence with a (typically large) set of other allele profiles. It counts the number of allelic differences between the profiles. If a certain profile has a difference count that is smaller than a cutoff value the profiles' mongo ID is reported back to the client.

### Input fields

- seq_collection: the MongoDB collection that contains the sequences
- filtering: a dictionary in the format {"field_1": "value_1", "field_2": "value_2"} for filtering the sequences
- profile_field_path: field (or dotted field path) for where Bio API should look for the cgMLST allele profiles to compare
- input_mongo_id: mongo id for the reference profile that has to be compared to others
- cutoff: integer value indicating the maximum allelic distance (maximum number of differences) between the input profile and the compared profile
- unknowns_are_diffs: Boolean value that indicates whether an unknown value in an allele profile should count as 'different' or 'equal'