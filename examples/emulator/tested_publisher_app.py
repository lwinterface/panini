from panini.emulator_client import EmulatorClient

filename = "resources/events.publisher.2021-03-19-16-21-30.jsonl"

client = EmulatorClient(
    filepath=filename,
    prefix='prefix',
    app_name='publisher',
)


@client.listen("listener.store.listen")
async def listen(topic, message):
    print(topic, message)


@client.listen("listener.store.request")
async def response(topic, message):
    print(topic, message)


if __name__ == "__main__":
    client.run()
