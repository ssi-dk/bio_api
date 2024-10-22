import asyncio
import uuid
import sys
import os
from dataclasses import asdict

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from calculations import SNPCalculation, HPCResources
from sofi_messenger.src import sofi_messenger
 
AMQP_HOST = os.getenv('AMQP_HOST', "amqp://guest:guest@rabbitmq/")

async def main() -> None:
    messenger = sofi_messenger.SOFIMessenger(AMQP_HOST)
    hpc_r: HPCResources = HPCResources()
    snp_calc = SNPCalculation(
        input_files=['file1', 'file2', 'file3'],
        output_dir='output_dir',
        reference='file4'
    )
    
    await messenger.send_hpc_call(
        uuid.uuid4().hex, #snp_calc._id,
        snp_calc.job_type,
        hpc_r.group,
        cpus=hpc_r.cpus,
        memGB=hpc_r.memGB,
        nodes=hpc_r.nodes,
        args=snp_calc.to_dict(),
    )


if __name__ == "__main__":
    asyncio.run(main())