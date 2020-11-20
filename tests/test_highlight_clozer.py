from app.card_generation.highlight_clozer import cloze_out_keyword, no_punc, _clean_keyword, get_keywords
from app.card_generation.readwise import _generate_clozed_highlight_notes
from app.models.base import User

# GIVEN keyword exists with punctuation in sentence
# WHEN getting the cloze version of the sentence
# THEN returns cloze that clozes the keyword and retains un-clozed punctuation
from tests.utils import TEST_USER


def test_cloze_out_keyword_with_punctuation():
    relevant_sentence = "We could have green eggs and ham, if we had some ham."
    keyword = "ham"
    expected_cloze = "We could have green eggs and {{c1::ham}}, if we had some {{c1::ham}}."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))


def test_cloze_out_keyword_with_hyphen():
    relevant_sentence = "My mother-in-law keeps telling me about her mother-in-law."
    keyword = "mother-in-law"
    expected_cloze = "My {{c1::mother-in-law}} keeps telling me about her {{c1::mother-in-law}}."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))


def test_no_punc_keeps_hyphens_in_middle():
    word_with_hypen = "mother-in-law"
    expected_no_punc_result = "mother-in-law"
    assert (no_punc(word_with_hypen) == expected_no_punc_result)


def test_no_punc_removes_hyphens_at_end():
    word_with_hypen = "mother-in-law-"
    expected_no_punc_result = "mother-in-law"
    assert (no_punc(word_with_hypen) == expected_no_punc_result)


def test_no_punc_removes_prefix():
    word_with_starting_punctuation = "?something?"
    expected_no_punc_result = "something"
    assert (no_punc(word_with_starting_punctuation) == expected_no_punc_result)


def test_clean_keyword():
    unclean_keywords = [
        "the United Kingdom",
        "a grasshopper",
        " an ugly duckling ",
        "the Duchess of Cambridge",
        "LeBron James",  # Ensure doesn't strip first word when not needed
    ]
    expected_cleaned_keywords = [
        "United Kingdom",
        "grasshopper",
        "ugly duckling",
        "Duchess of Cambridge",
        "LeBron James"
    ]
    assert len(unclean_keywords) == len(expected_cleaned_keywords)
    for i in range(len(unclean_keywords)):
        assert expected_cleaned_keywords[i] == _clean_keyword(unclean_keywords[i])


# GIVEN keyword appears multiple times with different capitalization
# WHEN clozing out the keyword
# THEN clozes out the capitalized and lower-case keyword
def test_cloze_out_keyword_capitalization():
    relevant_sentence = "Mountains that are tall are more interesting than mountains that are short."
    keyword = "mountains"
    expected_cloze = "{{c1::Mountains}} that are tall are more interesting than {{c1::mountains}} that are short."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))

def test_cloze_out_keyword_with_apostrophe():
    relevant_sentence = "Amdahl's law applies only to the cases where the problem size is fixed. In practice, as more computing resources become available, they tend to get used on larger problems (larger datasets), and the time spent in the parallelizable part often grows much faster than the inherently serial work. In this case, Gustafson's law gives a less pessimistic and more realistic assessment of the parallel performance."
    keyword="Gustafson"
    expected_cloze = "Amdahl's law applies only to the cases where the problem size is fixed. In practice, as more computing resources become available, they tend to get used on larger problems (larger datasets), and the time spent in the parallelizable part often grows much faster than the inherently serial work. In this case, {{c1::Gustafson}}'s law gives a less pessimistic and more realistic assessment of the parallel performance."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))

def test_cloze_out_keyword_with_apostrophe_followed_by_period():
    relevant_sentence = "Amdahl's law applies only to the cases where the problem size is fixed. In practice, as more computing resources become available, they tend to get used on larger problems (larger datasets), and the time spent in the parallelizable part often grows much faster than the inherently serial work. In this case, Gustafson's law gives a less pessimistic and more realistic assessment of the parallel performance. The good idea is Gustafson's."
    keyword="Gustafson"
    expected_cloze = "Amdahl's law applies only to the cases where the problem size is fixed. In practice, as more computing resources become available, they tend to get used on larger problems (larger datasets), and the time spent in the parallelizable part often grows much faster than the inherently serial work. In this case, {{c1::Gustafson}}'s law gives a less pessimistic and more realistic assessment of the parallel performance. The good idea is {{c1::Gustafson}}'s."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))

# GIVEN keyword contains multiple words
# WHEN clozing out the keyword
# THEN clozes out only full occurrences of all words in keyword
def test_cloze_out_multiword_keyword():
    relevant_sentence = "LeBron James is the greatest basketball player of all time. James is much better than the other players."
    keyword = "LeBron James"
    expected_cloze = "{{c1::LeBron James}} is the greatest basketball player of all time. James is much better than the other players."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))


# Verify that given some test highlights, the whole pipeline works
def test_end_to_end_cloze_generation():
    test_highlights = [
        {
            'id': "zdone:something:12345",
            'text': "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife",
            'source_title': "Pride and Prejudice",
            'source_author': "Jane Austen"
        },
        {
            'id': "zdone:something:1542415",
            'text': "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness, it was the spring of hope, it was the winter of despair.",
            'source_title': "A Tale of Two Cities",
            'source_author': "Charles Dickens"
        },
        {
            'id': "zdone:something:123456",
            'text': "",
            'source_title': "A Tale of Two Cities",
            'source_author': "Charles Dickens"
        }
    ]
    fake_user = User()
    fake_user.uses_rsAnki_javascript = True
    fake_user.api_key = "some-api-key-12345"
    # This will break if/when cloze field is moved to diff relevant position
    generated_notes = _generate_clozed_highlight_notes(test_highlights, [], fake_user)
    first_cloze_sentence = generated_notes[0].fields[2]
    # clozes should be deterministic given same version of spacy and same model used
    assert ("{{c1::Darkness}}" in first_cloze_sentence)

    # we shouldn't generate a cloze note if we can't cloze out anything in the text
    assert len(generated_notes) == 2


# Verify that given some test highlights, the whole pipeline works
def test_clozes_not_generated_for_very_short_highlight():
    short_highlight_id = "zdone:something:988243"
    test_highlights = [
        {
            'id': "zdone:something:12345",
            'text': "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife",
            'source_title': "Pride and Prejudice",
            'source_author': "Jane Austen"
        },
        {
            'id': "zdone:something:1542415",
            'text': "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness, it was the spring of hope, it was the winter of despair.",
            'source_title': "A Tale of Two Cities",
            'source_author': "Charles Dickens"
        },
        {
            'id': short_highlight_id,
            'text': "Abraham Lincoln",  # short highlight that should be filtered
            'source_title': "Team of Rivals",
            'source_author': "Doris Kearns Goodwin"
        }
    ]
    # This will break if/when cloze field is moved to diff relevant position
    generated_notes = _generate_clozed_highlight_notes(test_highlights, [], TEST_USER)
    assert (len(generated_notes) == 2)
    for note in generated_notes:
        assert (not note.fields[0] == short_highlight_id)
