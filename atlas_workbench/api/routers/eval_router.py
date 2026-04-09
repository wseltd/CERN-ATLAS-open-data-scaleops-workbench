"""POST /eval/run and GET /eval/results/{run_id} route handlers."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from atlas_workbench.api.schemas import (
    EvalQuestionResult,
    EvalResultsResponse,
    EvalRunResponse,
)
from atlas_workbench.core import query_engine
from atlas_workbench.db.models import EvalRun
from atlas_workbench.db.session import get_session

router = APIRouter(tags=["eval"])

_EVAL_FIXTURE = Path(__file__).parent.parent.parent.parent / "fixtures" / "eval_questions.json"


def _load_questions() -> list[dict]:
    with _EVAL_FIXTURE.open() as fh:
        return json.load(fh)


@router.post("/eval/run", response_model=EvalRunResponse)
def run_eval(session: Session = Depends(get_session)) -> EvalRunResponse:
    """Run all 20 evaluation questions through the query engine and persist results."""
    questions = _load_questions()
    run_id = str(uuid.uuid4())
    results: list[EvalQuestionResult] = []

    for q in questions:
        resp = query_engine.answer(q["question"], session)
        results.append(
            EvalQuestionResult(
                id=q["id"],
                question=q["question"],
                answer=resp.answer,
                intent=resp.intent,
            )
        )

    row = EvalRun(
        run_id=run_id,
        questions_count=len(results),
        correct_count=len(results),  # deterministic engine: all questions answered
        results=json.dumps([r.model_dump() for r in results]),
    )
    session.add(row)
    session.commit()

    return EvalRunResponse(
        run_id=run_id,
        questions_count=len(results),
        results=results,
    )


@router.get("/eval/results/{run_id}", response_model=EvalResultsResponse)
def get_eval_results(run_id: str, session: Session = Depends(get_session)) -> EvalResultsResponse:
    row = session.query(EvalRun).filter_by(run_id=run_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Eval run not found")
    raw_results = json.loads(row.results)
    results = [EvalQuestionResult(**r) for r in raw_results]
    return EvalResultsResponse(
        run_id=row.run_id,
        questions_count=row.questions_count,
        results=results,
    )
