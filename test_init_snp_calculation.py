import asyncio
import sys
import os
from calculations import SNPCalculation, HPCResources

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

async def main() -> None:
    hpc_r: HPCResources = HPCResources(cpus=2, memGB=8, nodes='1, 2')
    snp_calc = SNPCalculation(
        seq_collection='samples',
        seqid_field_path='what.ever',
        seq_mongo_ids=['putn4viwerunv', 'øwejmrvwtkjo', '98nviuetnvmn'],
        reference_mongo_id='dfgdæfgdfgm',
        depth='7',
        ignore_hz=False,
        hpc_resources = hpc_r,
    )
    print("Object created.")

    snp_calc._id = await snp_calc.insert_document()
    print("Object saved.")

    # await snp_calc.query_mongodb_for_file_names()

    # await snp_calc.calculate()


if __name__ == "__main__":
    asyncio.run(main())