import os
import pathlib
import shutil


class Global:
    def __init__(self):
        self.public_variable = 0
        self.another_variable = 0
        self.additional_variable = 0
        self.list_variable = []


testing_directory_path = pathlib.Path(__file__).parent.absolute()
