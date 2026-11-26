from dataclasses import replace

from pitranscriptor.project import Project
from pitranscriptor.review import compare_readings
from pitranscriptor.subtitles import Cue, Word


def test_context_review_finds_single_word_with_matching_neighbors_and_preserves_punctuation():
    words = (
        Word("iba", 200, 400, 0.8),
        Word("a", 400, 500, 0.9),
        Word("apagar,", 500, 800, 0.96),
        Word("pero", 800, 1100, 0.9),
        Word("esperé", 1200, 1500, 0.8),
    )
    original = Project(
        "clip.mp4",
        5000,
        (Cue(200, 800, "iba a apagar,", words[:3]), Cue(800, 1500, "pero esperé", words[3:])),
    )
    candidate = replace(words[2], text="pagar.", probability=0.66)
    edited = (*words[:2], candidate, *words[3:])
    second = Project("clip.mp4", 5000, (Cue(200, 1500, "iba a pagar. pero esperé", edited),))
    (suggestion,) = compare_readings(original, second)
    assert (suggestion.row, suggestion.word_index) == (0, 2)
    assert (suggestion.original.text, suggestion.alternative) == ("apagar,", "pagar,")
    assert (suggestion.before, suggestion.after) == ("iba a", "pero esperé")
    assert (suggestion.listen_start, suggestion.listen_end) == (200, 1650)
    assert not compare_readings(original, original)
    shifted = tuple(
        replace(word, start_ms=word.start_ms + 600, end_ms=word.end_ms + 600) for word in edited
    )
    assert not compare_readings(
        original, second.with_cues([Cue(800, 2100, second.cues[0].text, shifted)])
    )
    uncertain = (*edited[:2], replace(candidate, probability=0.2), *edited[3:])
    assert not compare_readings(
        original, second.with_cues([replace(second.cues[0], words=uncertain)])
    )
