from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.core.file_manager import open_directory_in_file_manager
from src.services.conflict_resolution_service import ConflictResolutionService
from src.services.problem_service import (
    AvailableProblemAction,
    ProblemActionItem,
    ProblemItem,
    ProblemOccurrenceItem,
    ProblemService,
)


class ProblemAvailableActionResponse(BaseModel):
    key: str
    label: str
    tone: str
    requires_confirmation: bool

    @classmethod
    def from_item(cls, item: AvailableProblemAction) -> "ProblemAvailableActionResponse":
        return cls(**item.__dict__)


class ProblemResponse(BaseModel):
    id: str
    fingerprint: str
    category: str
    severity: str
    state: str
    title: str
    summary: str
    task_id: str | None
    object_kind: str
    object_key: str
    object_path: str | None
    first_seen_at: float
    last_seen_at: float
    occurrence_count: int
    latest_run_id: str | None
    latest_event_id: str | None
    classifier_version: str
    resolution_verification: str | None
    resolved_at: float | None
    ignored_reason: str | None
    resolution_key: str | None
    operation_family: str | None
    actionability: str
    resolved_by_run_id: str | None
    resolved_by_event_id: str | None
    last_good_at: float | None
    available_actions: list[ProblemAvailableActionResponse]

    @classmethod
    def from_item(cls, item: ProblemItem) -> "ProblemResponse":
        payload = item.__dict__.copy()
        payload["available_actions"] = [
            ProblemAvailableActionResponse.from_item(action)
            for action in item.available_actions
        ]
        return cls(**payload)


class ProblemOccurrenceResponse(BaseModel):
    id: str
    problem_id: str
    source_kind: str
    source_id: str
    run_id: str | None
    event_id: str | None
    occurred_at: float
    evidence: dict[str, object]

    @classmethod
    def from_item(cls, item: ProblemOccurrenceItem) -> "ProblemOccurrenceResponse":
        try:
            evidence = json.loads(item.evidence_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            evidence = {"raw": "证据解析失败"}
        return cls(
            id=item.id,
            problem_id=item.problem_id,
            source_kind=item.source_kind,
            source_id=item.source_id,
            run_id=item.run_id,
            event_id=item.event_id,
            occurred_at=item.occurred_at,
            evidence=evidence if isinstance(evidence, dict) else {"value": evidence},
        )


class ProblemActionResponse(BaseModel):
    id: str
    problem_id: str
    action_key: str
    requested_at: float
    started_at: float | None
    finished_at: float | None
    result: str
    error_code: str | None
    error_message: str | None
    verification_result: str | None

    @classmethod
    def from_item(cls, item: ProblemActionItem) -> "ProblemActionResponse":
        return cls(**item.__dict__)


class ProblemListResponse(BaseModel):
    total: int
    items: list[ProblemResponse]


class ProblemSummaryResponse(BaseModel):
    total: int
    unresolved: int
    by_state: dict[str, int]
    by_category: dict[str, int]
    by_severity: dict[str, int]


class ProblemHistoryResponse(BaseModel):
    occurrences: list[ProblemOccurrenceResponse]
    actions: list[ProblemActionResponse]


class ProblemDetailResponse(BaseModel):
    problem: ProblemResponse
    history: ProblemHistoryResponse


class ProblemActionRequest(BaseModel):
    action_key: Literal[
        "retry_task",
        "open_local_folder",
        "use_local",
        "use_cloud",
    ]


router = APIRouter(prefix="/problems", tags=["problems"])
service = ProblemService()


def _service(request: Request) -> ProblemService:
    return getattr(request.app.state, "problem_service", service)


@router.get("/summary", response_model=ProblemSummaryResponse)
async def get_problem_summary(request: Request, refresh: bool = False) -> ProblemSummaryResponse:
    problem_service = _service(request)
    if refresh:
        await problem_service.refresh_sources()
    return ProblemSummaryResponse(**await problem_service.get_summary())


@router.get("", response_model=ProblemListResponse)
async def list_problems(
    request: Request,
    state: str = Query(default="open,in_progress,waiting"),
    categories: list[str] = Query(default_factory=list),
    severities: list[str] = Query(default_factory=list),
    task_id: str = Query(default=""),
    search: str = Query(default=""),
    since: float | None = Query(default=None),
    until: float | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    refresh: bool = Query(default=False),
) -> ProblemListResponse:
    problem_service = _service(request)
    if refresh:
        await problem_service.refresh_sources()
    total, items = await problem_service.list_problems(
        state=state,
        categories=categories,
        severities=severities,
        task_id=task_id,
        search=search,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    return ProblemListResponse(
        total=total,
        items=[ProblemResponse.from_item(item) for item in items],
    )


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem(request: Request, problem_id: str) -> ProblemDetailResponse:
    problem_service = _service(request)
    problem = await problem_service.get_problem(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    occurrences = await problem_service.list_occurrences(problem_id, limit=50, offset=0)
    actions = await problem_service.list_actions(problem_id, limit=50, offset=0)
    return ProblemDetailResponse(
        problem=ProblemResponse.from_item(problem),
        history=ProblemHistoryResponse(
            occurrences=[ProblemOccurrenceResponse.from_item(item) for item in occurrences],
            actions=[ProblemActionResponse.from_item(item) for item in actions],
        ),
    )


@router.get("/{problem_id}/history", response_model=ProblemHistoryResponse)
async def get_problem_history(
    request: Request,
    problem_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProblemHistoryResponse:
    problem_service = _service(request)
    if not await problem_service.get_problem(problem_id):
        raise HTTPException(status_code=404, detail="Problem not found")
    occurrences = await problem_service.list_occurrences(problem_id, limit=limit, offset=offset)
    actions = await problem_service.list_actions(problem_id, limit=limit, offset=offset)
    return ProblemHistoryResponse(
        occurrences=[ProblemOccurrenceResponse.from_item(item) for item in occurrences],
        actions=[ProblemActionResponse.from_item(item) for item in actions],
    )


@router.post("/{problem_id}/verify", response_model=ProblemResponse)
async def verify_problem(request: Request, problem_id: str) -> ProblemResponse:
    item = await _service(request).verify_problem(problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found")
    return ProblemResponse.from_item(item)


@router.post("/{problem_id}/actions", response_model=ProblemActionResponse)
async def execute_problem_action(
    request: Request,
    problem_id: str,
    payload: ProblemActionRequest,
) -> ProblemActionResponse:
    problem_service = _service(request)
    problem = await problem_service.get_problem(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    try:
        action = await problem_service.start_action(problem_id, payload.action_key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        verification_result = await _run_action(request, problem, payload.action_key)
        completed = await problem_service.finish_action(
            action.id,
            result="accepted",
            verification_result=verification_result,
        )
        return ProblemActionResponse.from_item(completed)
    except Exception as exc:
        failed = await problem_service.finish_action(
            action.id,
            result="failed",
            error_code=type(exc).__name__,
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "action": ProblemActionResponse.from_item(failed).model_dump()},
        ) from exc


async def _run_action(request: Request, problem: ProblemItem, action_key: str) -> str:
    if action_key in {"use_local", "use_cloud"}:
        occurrences = await _service(request).list_occurrences(problem.id, limit=1, offset=0)
        conflict_id = next(
            (item.source_id for item in occurrences if item.source_kind == "conflict"),
            None,
        )
        if not conflict_id:
            raise RuntimeError("Conflict source is unavailable")
        conflict_service = request.app.state.conflict_service
        resolver = ConflictResolutionService(conflict_service=conflict_service)
        result = await resolver.resolve_conflict(
            conflict_id,
            action_key,
            runner=getattr(request.app.state, "sync_runner", None),
        )
        if not result or not result.resolved:
            raise RuntimeError("Conflict resolution was not verified")
        return "source_resolved"

    if not problem.task_id:
        raise RuntimeError("Problem is not associated with a task")
    task_service = request.app.state.sync_task_service
    task = await task_service.get_task(problem.task_id)
    if not task:
        raise RuntimeError("Task not found")
    if action_key == "retry_task":
        request.app.state.sync_runner.start_task(task)
        return "waiting_for_later_run"
    if action_key == "open_local_folder":
        open_directory_in_file_manager(task.local_path)
        return "not_applicable"
    raise ValueError("Unsupported action")


__all__ = ["router", "service"]
