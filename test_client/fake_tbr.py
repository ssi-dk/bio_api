import pandas
import argparse
from faker import Faker
import random
from datetime import date, timedelta

fake = Faker('da_DK')

parser = argparse.ArgumentParser(
                prog='fake_tbr',
                description="Create fake TBR data for keys taken from first column in a semicolon separated data file. "
)

parser.add_argument('input_filename')
parser.add_argument('output_filename')
parser.add_argument('--limit', type=int, default=None)
args = parser.parse_args()

input_data = pandas.read_csv(args.input_filename, sep=';', encoding='ISO-8859-1')

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
pandas.set_option('display.max_columns', len(tbr_fields))

output_data = pandas.DataFrame(columns=tbr_fields)

for i_index, i_row in input_data.iterrows():
    if args.limit is not None and i_index > args.limit:
        break

    last_name = fake.last_name()
    male = bool(random.getrandbits(1))
    first_name = fake.first_name_male() if male else fake.first_name_female()
    age_timedelta = date.today() - fake.date_of_birth(maximum_age=90)
    age = age_timedelta.days // 365
    run_id = 'N_WGS_' + str(random.randint(0,100)).zfill(3)
    travel = bool(random.getrandbits(1))
    rejse = 'Ja' if travel else 'Nej'
    landnavn = fake.country().upper() if travel else ""
    provdato = fake.date_this_century()
    dato_kma = provdato + timedelta(days=random.randint(1, 5))
    dato_epi = dato_kma + timedelta(days=random.randint(1, 15))
    regionsnavn = fake.state()
    time_postfix =  ' 00:00:00'

    output_data.loc[i_index] = (
        i_row['Key'],
        # provdato example: '2015-01-14 00:00:00'
        str(provdato) + time_postfix,
        # RunID example: 'N_WGS_999'
        run_id,
        # cprnr example: '2512489996'
        fake.date_of_birth().strftime('%d%m%y') + '-' + str(fake.random_number(4, fix_len=True)),
        # kon example: 'K'
        'M' if male else 'K',
        # navn example: 'BERGGREN, NANCY ANN'
        f'{last_name}, {first_name}'.upper(),
        # alder example: 72
        age,
        # PrimaryIsolate example: 1
        1,
        # Rejse example: 'Ja'
        rejse,
        # landnavn example: 'IBIZA, MALLORCA'
        landnavn,
        # KMAdato example: '2015-01-20 00:00:00'
        str(dato_kma) + time_postfix,
        # kmanavn example: 'KMA RegionSjælland'
        'KMA Region ' + regionsnavn,
        # FUDNR example: '2211'
        '',
        # ClusterID example: 'ST99#99'
        '',
        # Dato_Epi example: '2024-03-22 18:59:01.917'
        str(dato_epi) + time_postfix,
        # Regionsnavn example: 'SJÆLLAND'
        regionsnavn.upper(),
        # Species example: 'Escherichia coli'
        'Campylobacter jejuni',
        # ST example: 583
        random.randint(1, 999)
    )

output_data.to_csv(args.output_filename, sep=';', index=False)