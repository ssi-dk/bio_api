import argparse
from datetime import datetime
from pathlib import Path
from json import dumps

from microreact_integration import common
from microreact_integration.functions import new_project_2

parser = argparse.ArgumentParser(description="Create a new minimal project in Microreact using a tree and a metadata table from files.")
parser.add_argument("metadata_url", help="URL with metadata")
parser.add_argument("metadata_columns", help="Comma-separated list with column names to import")
parser.add_argument("--tree", help="Path to a Newick file containing the initial tree")
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

print(f"Name of created project will be {args.project_name}")
columns = args.metadata_columns.split(',')

rest_response = new_project_2(
    project_name=args.project_name,
    metadata_url=args.metadata_url,
    columns=columns,
    tree_calcs=tree_calcs,
    mr_access_token=common.MICROREACT_ACCESS_TOKEN,
    mr_base_url=common.MICROREACT_BASE_URL,
    verify = not args.noverify
    )
print(f"HTTP response code: {str(rest_response)}")
print("Response as actual JSON:")
print(dumps(rest_response.json()))