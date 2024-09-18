import argparse
from datetime import datetime
from pathlib import Path
from json import dumps

from microreact_integration import common
from microreact_integration.functions import new_project

parser = argparse.ArgumentParser(description="Create a new minimal project in Microreact using an external url to a metadata table.")
parser.add_argument("metadata_url", help="URL to a metadata file")
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

print(f"Name of created project will be {args.project_name}")

rest_response = new_project(
    project_name=args.project_name,
    metadata_url = args.metadata_url,
    mr_access_token=common.MICROREACT_ACCESS_TOKEN,
    mr_base_url=common.MICROREACT_BASE_URL,
    verify = not args.noverify
    )
print(f"HTTP response code: {str(rest_response)}")
print("Response as actual JSON:")
print(dumps(rest_response.json()))