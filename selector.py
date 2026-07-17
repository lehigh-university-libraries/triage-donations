DEWEY_SELECTOR_MAP = {
    0: "Reference/General Selector",
    1: "Philosophy/Psychology Selector",
    2: "Religion Selector",
    3: "Social Sciences Selector",
    4: "Language Selector",
    5: "Science Selector",
    6: "Technology Selector",
    7: "Arts Selector",
    8: "Literature Selector",
    9: "History/Geography Selector",
}

DEFAULT_SELECTOR = "General Collections Selector"


def get_selector(call_number):
    """Stub. Maps a Dewey call number to a subject-selector librarian's name.

    call_number may be an empty string if no Dewey number was found.
    This is a placeholder for a future call to a real selector-lookup web service.
    """
    leading = (call_number or "").strip()
    if not leading or not leading[0].isdigit():
        return DEFAULT_SELECTOR

    first_digit = int(leading[0])
    return DEWEY_SELECTOR_MAP.get(first_digit, DEFAULT_SELECTOR)
