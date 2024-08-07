from pandas import read_csv, DataFrame
import argparse
from faker import Faker

fake = Faker('da_DK')

parser = argparse.ArgumentParser(
                prog='fake_tbr',
                description="Create fake TBR data for keys taken from first column in a semicolon separated data file. "
)

parser.add_argument('input_filename')
parser.add_argument('output_filename')
args = parser.parse_args()

input_data = read_csv(args.input_filename, sep=';', encoding='ISO-8859-1')

tbr_fields = (
    'Isolatnr',
    'provdato',
    'RunID',
    'cprnr',
    'kon',
    'navn',
    'alder',
    'PrimaryIsolate',
    'Rejse',
    'landnavn',
    'KMAdato',
    'kmanavn',
    'FUDNR',
    'ClusterID',
    'Dato_Epi',
    'Regionsnavn',
    'Species',
    'ST'
)


output_data = DataFrame(columns=tbr_fields)

for i_index, i_row in input_data.iterrows():
    output_data.loc[i_index] = (
        i_row.get('Isolatnr'),
        # provdato example: '2015-01-14 00:00:00'
        '2015-01-14 00:00:00',
        # RunID example: 'N_WGS_999'
        'N_WGS_999',
        # cprnr example: '2512489996'
        '2512489996',
        # kon example: 'K'
        'K',
        # navn example: 'BERGGREN, NANCY ANN'
        f'{fake.last_name()}, {fake.first_name()}'.upper(),
        # alder example: 72
        72,
        # PrimaryIsolate example: 1
        1,
        # Rejse example: 'Ja'
        'Ja',
        # landnavn example: 'IBIZA, MALLORCA'
        'IBIZA, MALLORCA',
        # KMAdato example: '2015-01-20 00:00:00'
        '2015-01-20 00:00:00',
        # kmanavn example: 'KMA RegionSjælland'
        'KMA RegionSjælland',
        # FUDNR example: '2211'
        '2211',
        # ClusterID example: 'ST99#99'
        'ST99#99',
        # Dato_Epi example: '2024-03-22 18:59:01.917'
        '2024-03-22 18:59:01.917',
        # Regionsnavn example: 'SJÆLLAND'
        'SJÆLLAND',
        # Species example: 'Escherichia coli'
        'Escherichia coli',
        # ST example: 583
        583
    )
    print(output_data)

# output = fake_fn(keys)
