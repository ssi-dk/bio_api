from os import getenv
from pandas import read_csv, DataFrame
import argparse
import pymongo
import json

from client_functions import dictify_path, recursive_merge

def fake_fn(
            db,
            data_filename: str,
            mapping_filename: str,
            allele_filename: str,
            collection: str='samples',
            max_items: int=None):
    
    input_df = read_csv(data_filename, sep=';', encoding='ISO-8859-1')
    
    mapping_df = read_csv(mapping_filename, sep=';', encoding='ISO-8859-1')
    conversion_dict = dict()
    for i in mapping_df.iterrows():
        conversion_entry = i[1].to_dict()
        conversion_dict[conversion_entry['import_column']] = conversion_entry['sofi_fieldname']

    sofi_field_df = read_csv('SOFI_fields.csv', sep=';', encoding='ISO-8859-1')
    print(sofi_field_df)
    sofi_field_dict = dict()
    for _index, row in sofi_field_df.iterrows():
        if not row[2] in ['-', '?']:
            sofi_field_dict[row[1]] = row[2]
    print("SOFI field dict:")
    print(sofi_field_dict)


    inserted_ids = list()
    unnested_document = dict()
    for _index, row in input_df.iterrows():
        if max_items and (_index >= max_items):
            print(f"Reached maximum of {max_items} items.")
            break

        sequence_id = row[0]
        print(f"Sequence ID: {sequence_id}")

        # Each rows' to_dict() will be a MongoDB document
        data_dict = row.to_dict()
        for key, value in data_dict.items():
            sofi_field_name = conversion_dict.get(key)
            if sofi_field_name:
                if sofi_field_name == 'ST':
                    # Need to add a schema name
                    try:
                        unnested_document[sofi_field_name] = {'some_schema': int(value)}
                    except ValueError:
                        unnested_document[sofi_field_name] = dict()
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        try:
                            value = int(value)
                        except ValueError:
                            pass
                    unnested_document[sofi_field_name] = value
        
        print("Unnested document:")
        print(unnested_document)
        print()

        document = dict()
        for key, value in unnested_document.items():
            dotted_path = sofi_field_dict[key]
            nested_dict = dictify_path(dotted_path, value)
            document = recursive_merge(document, nested_dict)

        print("Nested document:")    
        print(document)
        print()

        # Add allele profile
        allele_df = read_csv(allele_filename, sep='\t')
        allele_df = allele_df[['key']].assign(
                    alleles=allele_df.set_index(['key']).to_dict(orient='records')
        )
        allele_df = allele_df.set_index(['key'])
        print(allele_df)
        allele_df_as_dict = allele_df.to_dict()
        alleles = allele_df_as_dict['alleles'][sequence_id]

        # Convert values to int if possible
        for locus, value in alleles.items():
            try:
                alleles[locus] = int(value)
            except ValueError:
                pass

        alleles_dict = dictify_path('categories.cgmlst.report.alleles', alleles)
        # print("Alleles dict:")
        # print(alleles_dict)
        document = recursive_merge(document, alleles_dict)
        # print("Document with allele profile")
        # print(document)

        result = db[collection].insert_one(document)
        assert result.acknowledged == True
        inserted_ids.append(str(result.inserted_id))
    return inserted_ids

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
            i_row[0],
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
