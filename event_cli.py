import argparse
from pathlib import Path
from agentic_qa.event_router import Event, run_event

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("event",type=Path)
    p.add_argument("--output",type=Path,default=Path("artifacts/event/report.json"))
    a=p.parse_args()
    run_event(Event.model_validate_json(a.event.read_text()),a.output)
