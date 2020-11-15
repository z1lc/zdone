from app.card_generation.highlight_clozer import cloze_out_keyword, no_punc


# GIVEN keyword exists with punctuation in sentence
# WHEN getting the cloze version of the sentence
# THEN returns cloze that clozes the keyword and retains un-clozed punctuation
def test_cloze_out_keyword_with_punctuation():
    relevant_sentence = "We could have green eggs and ham, if we had some ham."
    keyword = "ham"
    expected_cloze = "We could have green eggs and {{c1::ham}}, if we had some {{c1::ham}}."
    assert(expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))

def test_cloze_out_keyword_with_hyphen():
    relevant_sentence = "My mother-in-law keeps telling me about her mother-in-law."
    keyword = "mother-in-law"
    expected_cloze = "My {{c1::mother-in-law}} keeps telling me about her {{c1::mother-in-law}}."
    assert(expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))

def test_no_punc_keeps_hyphens_in_middle():
    word_with_hypen = "mother-in-law"
    expected_no_punc_result = "mother-in-law"
    assert(no_punc(word_with_hypen) == expected_no_punc_result)

def test_no_punc_removes_hyphens_at_end():
    word_with_hypen = "mother-in-law-"
    expected_no_punc_result = "mother-in-law"
    assert(no_punc(word_with_hypen) == expected_no_punc_result)

def test_no_punc_removes_prefix():
    word_with_starting_punctuation ="?something?"
    expected_no_punc_result = "something"
    assert(no_punc(word_with_starting_punctuation) == expected_no_punc_result)

# GIVEN keyword appears multiple times with different capitalization
# WHEN clozing out the keyword
# THEN clozes out the capitalized and lower-case keyword
def test_cloze_out_keyword_capitalization():
    relevant_sentence = "Mountains that are tall are more interesting than mountains that are short."
    keyword = "mountains"
    expected_cloze = "{{c1::Mountains}} that are tall are more interesting than {{c1::mountains}} that are short."
    assert (expected_cloze == cloze_out_keyword(keyword, 0, relevant_sentence))
