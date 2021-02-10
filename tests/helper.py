import os
import pathlib
import shutil


class Global:
    def __init__(self):
        self.public_variable = 0
        self.another_variable = 0
        self.additional_variable = 0


testing_directory_path = pathlib.Path(__file__).parent.absolute()


def get_testing_logs_directory_path(
    folder: str = "logs", remove_if_exist: bool = False
):
    testing_logs_directory_path = os.path.join(testing_directory_path, folder)
    if remove_if_exist:
        if os.path.exists(testing_logs_directory_path):
            shutil.rmtree(testing_logs_directory_path)

    return testing_logs_directory_path
