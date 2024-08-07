from pandas import read_csv, DataFrame
import argparse

if __name__ == '__main__':
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
        print(output_data)
    
    # output = fake_fn(keys)
