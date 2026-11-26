from agentic_qa.event_router import Event, run_event, flakiness

def test_coverage(tmp_path):
    e=Event(kind="coverage",event_id="1",evidence={"required_tests":["a","b"],"executed_tests":["a"]})
    assert run_event(e,tmp_path/"report.json")=={"missing":["b"],"coverage_percent":50.0}

def test_flakiness():
    assert flakiness({"runs":[{"revision":"x","tests":{"a":"passed"}},{"revision":"x","tests":{"a":"failed"}},{"revision":"y","tests":{"b":"failed"}}]})["suspected_flaky"]==[{"revision":"x","test":"a"}]
