import argparse
from pathlib import Path
from os.path import splitext
from json import dump

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="Semiconon-separated file containing mapping beteen BN column names and SOFi column names")
args = parser.parse_args()

input_file = Path(args.input_file)
output_filename: str = splitext(args.input_file)[0] + '.json'
print(f"Output filename: {output_filename}")

mapping = dict()

with open(input_file, encoding="ISO-8859-1") as i:
    while True:
        try:
            conversion_entry = i.readline().strip().split(";")
            mapping[conversion_entry[0]] = conversion_entry[1].lower()
        except IndexError:
            break

print(mapping)

with open(Path(output_filename), 'w') as o:
    dump(mapping, o, indent=4, ensure_ascii=False)