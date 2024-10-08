import asyncio
import uuid
import sys

import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from sofi_messenger.src import sofi_messenger
 
 
async def main() -> None:
    host = "amqp://guest:guest@localhost/"
    messenger = sofi_messenger.SOFIMessenger(host)
 
    hpc_resources = {
        #"args": ["-h"],
        "cpus": 1,  # Max is 40
        "memGB": 4,  # Max is 185 (GB)
        "group": "fvst_ssi",
        "nodes": "1",
        # "walltime": "24:00:00",
    }
 
    snp_args = {
        "--input_files": "/path/to/some/file, /path/to/some/other/file",
        "—output_dir": "/path/to_output_dir"
        "--reference: /path/to/reference",
        "--depth": "15",
        "--ignore_heterozygous": "TRUE"
    }
 
    job_uuid = uuid.uuid4().hex
 
    await messenger.send_hpc_call(
        uuid=job_uuid,
        job_type="snp",
        args=snp_args,
        **hpc_resources,
    )
 
 
if __name__ == "__main__":
    asyncio.run(main())