import asyncio
import sys
import os

from calculations import SNPCalculation, HPCResources, MissingDataException

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

async def main() -> None:
    hpc_r: HPCResources = HPCResources(cpus=2, memGB=8, nodes='1, 2')
    snp_calc = SNPCalculation(
        seq_collection='campy_2019',
        seqid_field_path='categories.sample_info.summary.sofi_sequence_id',
        filename_field_path='categories.contigs.summary.data',
        seq_mongo_ids=['666febab9871ba945a1a11f0', '666febac9871ba945a1a11f1', '666febad9871ba945a1a11f2'],
        reference_mongo_id='666febad9871ba945a1a11f3',
        depth='7',
        ignore_hz=False,
    )
    print("Object created.")

    snp_calc._id = await snp_calc.insert_document()
    print("Object saved.")

    
    profile_count, cursor = await snp_calc.query_mongodb_for_filenames()

    await snp_calc.calculate()


if __name__ == "__main__":
    asyncio.run(main())