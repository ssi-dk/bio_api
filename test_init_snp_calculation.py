import asyncio
import sys
import os
from calculations import SNPCalculation, HPCResources

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

async def main() -> None:
    hpc_r: HPCResources = HPCResources()
    snp_calc = SNPCalculation(
        # hpc_resources = hpc_r
        input_files=['file1', 'file2', 'file3'],
        output_dir='output_dir',
        reference='file4'
    )
    snp_calc._id = await snp_calc.insert_document()
    await snp_calc.calculate()


if __name__ == "__main__":
    asyncio.run(main())