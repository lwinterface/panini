from panini.emulator_client import EmulatorClient

filename = "resources/events.listener.2021-03-19-16:21:13.jsonl"

client = EmulatorClient(
    filepath=filename,
    prefix='prefix',
    app_name='listener'
)


# check response from target app
@client.listen("listener.store.request.reply")
def request_reply(topic, message):
    print(f"request reply, {topic} {message}")



if __name__ == "__main__":
    client.run()
