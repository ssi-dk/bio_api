#!/usr/bin/env python

from os import getenv
from mongo import Config, MongoAPI
import yaml
import argparse
from pprint import pprint

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://localhost:27017/bio_api_test')

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=argparse.FileType('r'), default="example_config.yaml", help="config to load into database" )
    return parser.parse_args()


def main():
    args = parse_arguments()
    mongoapi = MongoAPI(MONGO_CONNECTION_STRING)
    yaml_config = yaml.safe_load(args.config)
    #pprint(yaml_config)
    #pprint([x['section'] for x in yaml_config if x["section"]=="snp"])
    config = Config(mongoapi)
    config.clear()
    config.load(yaml_config)

if __name__ == "__main__":
    main()