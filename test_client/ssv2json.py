import argparse
from pathlib import Path
from os.path import splitext
from json import dump

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="Semiconon-separated file with BN column names in the first line")
args = parser.parse_args()

input_file = Path(args.input_file)
output_filename: str = splitext(args.input_file)[0] + '.json'
print(f"Output filename: {output_filename}")

with open(input_file, encoding="ISO-8859-1") as i:
    bn_colnames = i.readline().strip().split(";")

mapping = dict()
for colname in bn_colnames:
    mapping[colname] = ''

with open(Path(output_filename), 'w') as o:
    dump(mapping, o, indent=4, ensure_ascii=False)