from panini import app as panini_app

app = panini_app.App(
    service_name="separate_file",
    host="127.0.0.1",
    port=4222,
    logger_in_separate_process=False,
)


@app.listen("separate_file.listen_request")
async def listen_request(msg):
    return {"success": True, "message": "separate_file.listen_request"}


if __name__ == "__main__":
    app.start()
