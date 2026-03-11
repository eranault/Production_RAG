import requests 

connector_config = {
    "name": "mongodb_connector",
    "config": {
        "connector.class": "io.debezium.connector.mongodb.MongoDbConnector",
        "mongodb.connection.string": "mongodb://mongo1:27017/?replicaSet=rs0",
        "collection.include.list": "hackernews.stories",
        "topic.prefix": "dbz",
        "capture.mode": "change_streams_update_full"
    }
}

response = requests.post(
    "http://localhost:8083/connectors",
    json=connector_config
)

print(response.status_code)
print (response.json ())