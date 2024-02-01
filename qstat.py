from os import getenv
import datetime

import pymongo
from pymongo import InsertOne, DeleteMany, ReplaceOne, UpdateOne

from persistence import mongo

from aio_pika import connect_robust
from aio_pika.patterns import RPC

__all__ = [
    'consume_qstat'
]

mongo_connection = getenv('MONGO_CONNECTION')

# TODO: remove?
mongo_api = mongo.MongoAPI(mongo_connection)

class OutputConverter:
    def __init__(self, console_output: str):
        lines = console_output.split("\n")[:-1]
        self.header_line = lines.pop(0)
        self.dash_line = lines.pop(0)
        self.value_lines = lines
        for char in self.dash_line:
            assert char in ('-', ' ')
        dash_list = self.dash_line.split(' ')
        self.column_widths = [ len(element) for element in dash_list ]

    def get_items(self, line):
        items = list()
        for width in self.column_widths:
            item = line[:width + 1].strip()
            items.append(item)
            line = line[width + 1:]
        return items

    def get_headers(self):
        return self.get_items(self.header_line)
    
    def get_keys(self):
        # Get headers in 'key_friendly' format
        keys = list()
        for header in self.get_headers():
            header = header.replace(' ', '_')
            key = ''
            for char in header:
                key += char.lower()
            keys.append(key)
        return keys

    def get_value_rows(self):
        value_rows = list()
        for line in self.value_lines:
            value_rows.append(self.get_items(line))
        return value_rows

    def get_rows(self):
        pass


async def consume_qstat(loop):
    # TODO Define url in docker-compose.yml
    connection = await connect_robust(host='rabbitmq', loop=loop)
    channel = await connection.channel()
    queue_name = "qstat"
    # routing_key = "qstat"
    # exchange = await channel.declare_exchange("direct", auto_delete=True)
    queue = await channel.declare_queue(queue_name, auto_delete=True)

    async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    # Use a mongoish timestamp
                    timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

                    message_body = message.body.decode()
                    if message_body.startswith("Problem"):
                        print(f"qstat says: {message_body.strip()}")
                    elif message_body == '':
                        # No HPC jobs seem to be queued or running.
                        # Check in MongoDB if any jobs there have s != 'C'
                        jobs_with_wrong_statuses = mongo_api.find_unfinished_jobs()
                        job_ids_to_fix = [ job['job_id'] for job in jobs_with_wrong_statuses]
                        if len(job_ids_to_fix) > 0:
                            message = "These jobs seem to have a wrong status in db: "
                            message += " ".join(job_ids_to_fix)
                            print(message)
                            bulk_writes = list()
                            for job_id in job_ids_to_fix:
                                bulk_writes.append(
                                    UpdateOne(
                                        {"job_id": job_id}, {"$set": {
                                            "timestamp": timestamp,
                                            "s": "C",
                                    }})
                                )
                    else:
                        try:
                            oc = OutputConverter(message_body)
                            keys = oc.get_keys()
                            value_rows = oc.get_value_rows()
                        except Exception as e:
                            print(f"Could not parse qstat output: {e}")
                            continue

                        # entries = job entries within this RabbitMQ message
                        entries = list()

                        for row in value_rows:
                            new_entry = dict()
                            for key in keys:
                                new_entry[key] = row.pop(0)
                            entries.append(new_entry)
                        print("Job entries from qstat:")
                        print(entries)
                        job_ids = [ entry['job_id'] for entry in entries ]
                        print("Job ids that will be inserted or updated:")
                        print(job_ids)           
                        bulk_writes = list()
                        for job_id in entries:
                            bulk_writes.append(
                                UpdateOne(
                                    {"job_id": job_id['job_id']}, {"$set": {
                                        "timestamp": timestamp,
                                        "name": job_id["name"],
                                        "username": job_id["username"],
                                        "time_use": job_id["time_use"],
                                        "s": job_id["s"],
                                        "queue": job_id["queue"],
                                    }},upsert=True)
                            )
                        mongo_api.db.hpc_jobs.bulk_write(bulk_writes)
                    
