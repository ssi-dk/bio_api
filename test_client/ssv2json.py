with open('input_data/Campy2019_metadata_20240530.csv', encoding="ISO-8859-1") as f:
    bn_colnames = f.readline().strip().split(";")

mapping = dict()
for colname in bn_colnames:
    mapping[colname] = ''

print(mapping)