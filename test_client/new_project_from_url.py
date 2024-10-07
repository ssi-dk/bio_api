import argparse
from datetime import datetime
from pathlib import Path
from json import dumps, JSONDecodeError

from microreact_integration import common
from microreact_integration.functions import new_project_2

parser = argparse.ArgumentParser(description="Create a new minimal project in Microreact using a tree and a metadata table from files.")
parser.add_argument("metadata_url", help="URL with metadata")
parser.add_argument("metadata_columns", help="Comma-separated list with column names to import")
parser.add_argument("--hidden", help="Comma-separated list of columns to be hidden")
parser.add_argument("--tree", help="Path to a Newick file containing the initial tree")
parser.add_argument("--distances", help="Path to a CSV file with a distance matrix")
parser.add_argument(
    "--project_name",
    help="Project name (can be changed later in web interface)",
    default=common.USERNAME + '_' + str(datetime.now().isoformat(timespec='seconds'))
    )
parser.add_argument(
    "--noverify",
    help="Do not verify SSL certificate of Microreact host ",
    action="store_true"
    )
args = parser.parse_args()

if args.tree:
    with open(Path(args.tree), 'r') as tree_file:
        newick = tree_file.read()
        tree_calcs=[{'method': 'single', 'result': newick}]
else:
        tree_calcs = list()

raw_matrices = list()
if args.distances:
    with open(Path(args.distances), 'r') as dist_file:
        raw_matrices.append(dist_file.read())

print(f"Name of created project will be {args.project_name}")
columns = args.metadata_columns.split(',')

rest_response = new_project_2(
    project_name=args.project_name,
    metadata_url=args.metadata_url,
    columns=columns,
    tree_calcs=tree_calcs,
    hidden=args.hidden,
    raw_matrices=raw_matrices,
    mr_access_token=common.MICROREACT_ACCESS_TOKEN,
    mr_base_url=common.MICROREACT_BASE_URL,
    verify = not args.noverify
    )
print(f"HTTP response code: {str(rest_response)}")
print("response.content:")
print(str(rest_response.content))
try:
    print("Try to parse response as JSON")
    print(dumps(rest_response.json()))
except JSONDecodeError:
     print("Could not parse response as JSON")