from engine.script.parser import parse_script

VALID_SCRIPT = """JADE [angry, 0.8]: You knew!
RON [smug]: Of course.
JADE: Why?
"""


def test_valid_script_has_lines_and_speakers_in_order():
    parsed = parse_script(VALID_SCRIPT)

    assert parsed.errors == []
    assert parsed.warnings == []
    assert parsed.speakers == ["JADE", "RON"]
    assert [line.speaker for line in parsed.lines] == ["JADE", "RON", "JADE"]
    first_line = parsed.lines[0]
    assert (first_line.emotion, first_line.intensity, first_line.tagged) == ("angry", 0.8, True)
    assert first_line.text == "You knew!"
    untagged_line = parsed.lines[2]
    assert (untagged_line.emotion, untagged_line.intensity, untagged_line.tagged) == (None, None, False)


def test_speaker_names_are_upper_cased():
    parsed = parse_script("jade: Hi.\nRon: Hello.")

    assert parsed.speakers == ["JADE", "RON"]


def test_emotion_aliases_map_to_presets():
    parsed = parse_script("JADE [annoyed]: Hi.\nRON [Worried, 0.5]: Hello.")

    assert parsed.warnings == []
    assert parsed.lines[0].emotion == "angry"
    assert parsed.lines[1].emotion == "scared"


def test_unknown_emotion_warns_with_a_suggestion_and_plays_neutral():
    parsed = parse_script("JADE [grumpy]: Hi.\nRON: Hello.")

    assert parsed.errors == []
    assert len(parsed.warnings) == 1
    warning = parsed.warnings[0]
    assert warning.line_no == 1
    assert "grumpy" in warning.message
    assert "Try" in warning.message
    assert parsed.lines[0].emotion == "neutral"


def test_intensity_is_clamped_with_a_warning():
    parsed = parse_script("JADE [angry, 5]: Hi.\nRON [sad, 0]: Hello.")

    assert parsed.lines[0].intensity == 1.0
    assert parsed.lines[1].intensity == 0.1
    assert len(parsed.warnings) == 2


def test_mid_line_tag_warns_and_is_removed_from_the_text():
    parsed = parse_script("JADE: You knew [angry] about it.\nRON: Hello.")

    assert len(parsed.warnings) == 1
    assert "middle" in parsed.warnings[0].message
    assert parsed.lines[0].text == "You knew about it."


def test_fewer_than_two_speakers_is_an_error():
    parsed = parse_script("JADE: Hi.\nJADE: Anyone?")

    assert len(parsed.errors) == 1
    assert parsed.errors[0].line_no is None
    assert "2 to 6" in parsed.errors[0].message


def test_more_than_six_speakers_is_an_error():
    script = "\n".join(f"PERSON{number}: Hello." for number in range(7))

    parsed = parse_script(script)

    assert len(parsed.errors) == 1
    assert "7" in parsed.errors[0].message


def test_six_speakers_is_fine():
    script = "\n".join(f"PERSON{number}: Hello." for number in range(6))

    assert parse_script(script).errors == []


def test_notes_and_blank_lines_are_skipped():
    parsed = parse_script("# a note\n\n   \nJADE: Hi.\n  # indented note\nRON: Hello.\n")

    assert len(parsed.lines) == 2
    assert parsed.issues == []
    assert [line.line_no for line in parsed.lines] == [4, 6]


def test_line_without_a_colon_is_an_error():
    parsed = parse_script("JADE: Hi.\nthis is not dialogue\nRON: Hello.")

    assert len(parsed.errors) == 1
    assert parsed.errors[0].line_no == 2


def test_empty_script_is_an_error():
    parsed = parse_script("")

    assert len(parsed.errors) == 1
    assert parsed.lines == []


def test_estimated_length_is_positive_and_grows_with_the_script():
    short = parse_script("JADE: Hi there.\nRON: Hello.")
    longer = parse_script(VALID_SCRIPT * 5)

    assert short.estimated_length_s > 0
    assert longer.estimated_length_s > short.estimated_length_s


def test_to_dict_matches_the_api_shape():
    result = parse_script(VALID_SCRIPT).to_dict()

    assert set(result) == {"lines", "speakers", "issues", "error_count", "warning_count", "estimated_length_s"}
    assert set(result["lines"][0]) == {"line_no", "speaker", "emotion", "intensity", "text", "tagged"}
