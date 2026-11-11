from pathlib import Path
from types import SimpleNamespace
import pytest
from agentic_qa.evidence import junit_counts, write_report

def test_junit_counts(tmp_path):
    xml = '<testsuite><testcase name="a"/><testcase name="b"><failure/></testcase><testcase name="c"><skipped/></testcase></testsuite>'
    path = tmp_path / "junit.xml"
    path.write_text(xml)
    assert junit_counts(path) == {"status":"valid","total":3,"passed":1,"failed":1,"errors":0,"skipped":1}

def test_missing_junit_blocks_green(tmp_path):
    cases = SimpleNamespace(cases=[1])
    report = write_report(tmp_path, "requirement", "test-model", {"passed":True,"cases":cases,"code":"test"})
    assert report["status"] == "failed"
    assert (tmp_path / "report.json").exists()

def test_passed_junit(tmp_path):
    (tmp_path / "junit.xml").write_text('<testsuite><testcase name="a"/></testsuite>')
    cases = SimpleNamespace(cases=[1])
    assert write_report(tmp_path, "req", "model", {"passed":True,"cases":cases})["status"] == "passed"

def test_malformed_junit_raises(tmp_path):
    (tmp_path / "junit.xml").write_text("<broken")
    with pytest.raises(Exception):
        junit_counts(tmp_path / "junit.xml")
