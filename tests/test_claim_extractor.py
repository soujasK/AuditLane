from auditline.claim_extractor import extract_claims, extract_claims_from_pr


def test_extracts_at_mention_after_confirmed_with():
    text = "As confirmed with @sarah_dba during standup, this is safe to drop the legacy table."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].authorizer_name == "@sarah_dba"


def test_extracts_role_phrase_before_verb():
    text = "The architect verbally cleared this breaking schema change during standup."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].authorizer_name == "The architect"


def test_extracts_proper_name_after_confirmed_with():
    text = "Confirmed with Sarah that dropping v1_accounts is fine."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].authorizer_name == "Sarah"


def test_does_not_extract_from_ordinary_sentence():
    text = "Fixed the login bug and confirmed with unit tests that everything passes."
    claims = extract_claims(text)
    assert claims == []


def test_no_claims_returns_empty_list():
    text = "This PR just renames a variable for clarity, no behavior change."
    assert extract_claims(text) == []


def test_deduplicates_identical_sentence_name_pairs():
    text = "Confirmed with Sarah that this is fine. Confirmed with Sarah that this is fine."
    claims = extract_claims(text)
    # An exact duplicate sentence is the same claim restated, not two
    # distinct claims — one call to Sarah is enough, not two.
    assert len(claims) == 1
    assert claims[0].authorizer_name == "Sarah"


def test_sentence_initial_capitalized_filler_is_not_mistaken_for_a_name():
    text = "As confirmed with @sarah_dba during standup, this is safe to drop the legacy table."
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].authorizer_name == "@sarah_dba"


def test_markdown_line_wrap_does_not_truncate_the_claim():
    # A single newline is a soft wrap, not a sentence boundary — common
    # in markdown PR bodies. Only a blank line (paragraph break) should
    # end a sentence early.
    text = (
        "The architect verbally cleared this breaking schema change during\n"
        "today's standup, so merging this once CI is green."
    )
    claims = extract_claims(text)
    assert len(claims) == 1
    assert claims[0].claim_text == (
        "The architect verbally cleared this breaking schema change during "
        "today's standup, so merging this once CI is green."
    )


def test_extract_claims_from_pr_uses_title_as_subject_fallback():
    claims = extract_claims_from_pr(
        title="Drop legacy v1_accounts table",
        body="Cleared with the lead database admin during today's standup.",
    )
    assert len(claims) == 1
    assert claims[0].authorizer_name == "the lead database admin"
    assert claims[0].subject == "Drop legacy v1_accounts table"
