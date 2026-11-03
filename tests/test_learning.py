from agentic_qa.learning import examples, remember

def test_only_validated_repairs_are_stored(tmp_path):
    db = tmp_path / "repairs.sqlite3"
    assert remember(db, "failure", "fix", validated=False) is False
    assert examples(db) == []
    assert remember(db, "failure", "fix", validated=True) is True
    assert examples(db) == [("failure", "fix")]
    remember(db, "failure", "fix", validated=True)
    assert len(examples(db)) == 1
