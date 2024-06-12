import argparse
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="Semiconon-separated file with BN column names in the first line")
args = parser.parse_args()

input_file = pathlib.Path(args.input_file)

with open(input_file, encoding="ISO-8859-1") as f:
    bn_colnames = f.readline().strip().split(";")

mapping = dict()
for colname in bn_colnames:
    mapping[colname] = ''

print(mapping)