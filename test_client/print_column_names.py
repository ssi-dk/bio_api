with open('input_data/Campy2019_metadata_20240530.csv', encoding="ISO-8859-1") as f:
    names = f.readline().split(";")
for name in names:
    print(name)