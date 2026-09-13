from auditline.entailment import HeuristicEntailmentEngine
from auditline.models import EntailmentLabel


def make_engine():
    return HeuristicEntailmentEngine()


def test_contradiction_when_statement_denies_matching_topic():
    engine = make_engine()
    claim = "Sarah confirmed dropping v1_accounts across regional shards is safe."
    statement = (
        "No, dropping v1_accounts across regional shards is not safe, we agreed "
        "to keep it for backward compatibility."
    )
    result = engine.score(claim, statement)
    assert result.label == EntailmentLabel.CONTRADICTION
    assert result.confidence > 0.5


def test_entailment_when_statement_confirms_matching_topic():
    engine = make_engine()
    claim = "The architect verbally cleared dropping the v1_accounts table."
    statement = "Yes, I cleared dropping the v1_accounts table this morning."
    result = engine.score(claim, statement)
    assert result.label == EntailmentLabel.ENTAILMENT
    assert result.confidence > 0.5


def test_neutral_when_statement_hedges():
    engine = make_engine()
    claim = "Sarah confirmed the migration is safe."
    statement = "I'm not sure, I don't recall discussing that."
    result = engine.score(claim, statement)
    assert result.label == EntailmentLabel.NEUTRAL


def test_neutral_when_topics_do_not_overlap():
    engine = make_engine()
    claim = "Sarah confirmed the migration is safe."
    statement = "I spent the morning fixing the office coffee machine."
    result = engine.score(claim, statement)
    assert result.label == EntailmentLabel.NEUTRAL


def test_neutral_on_empty_statement():
    engine = make_engine()
    result = engine.score("Sarah confirmed it.", "")
    assert result.label == EntailmentLabel.NEUTRAL
