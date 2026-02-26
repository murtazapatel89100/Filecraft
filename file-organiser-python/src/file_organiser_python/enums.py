from enum import Enum


class SeparateOptions(Enum):
    IMG = "img"
    VIDEO = "video"
    ALL = "all"
    PDF = "pdf"
    PPT = "ppt"
    SHEET = "sheet"
    DOC = "doc"
    AUDIO = "audio"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    FONT = "font"
    DISK_IMAGE = "disk_image"
    CODE = "code"


class SeparateChoices(Enum):
    EXTENSION = "extension"
    DATE = "date"
    EXTENSION_AND_DATE = "extension_and_date"
