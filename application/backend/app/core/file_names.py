"""Turn a title or a character name into something safe to use as a file name."""

import re

UNSAFE_FILE_NAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_FILE_NAME_LENGTH = 100


def safe_file_name(text: str, fallback: str) -> str:
    cleaned = UNSAFE_FILE_NAME_CHARACTERS.sub(" ", text)
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned[:MAX_FILE_NAME_LENGTH].strip(" .") or fallback
