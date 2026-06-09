import json
import hashlib
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func

from app.config import settings, ensure_dirs, normalize_competition_name
from app.database import init_db, SessionLocal
from app.llm.base import LLMFactory
from app.orchestrator import Orchestrator, ReviewReport
from app.models.submission import Submission, Review, CalibrationRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ensure_dirs()
init_db()

app = FastAPI(title="AcademicReviewer", version="0.2.0")

SUBMISSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "submissions"
_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def _get_llm():
    return LLMFactory.create(settings.llm_provider)


def _convert_report_to_json(report: ReviewReport) -> str:

    def _serialize(obj):
        return str(obj)

    import json as _json
    return _json.dumps(report.__dict__, default=_serialize, ensure_ascii=False)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/review")
async def review_document(
    file: UploadFile = File(...),
    competition: str = Form(...),
    student_name: str = Form(""),
    model_provider: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    provider = model_provider or settings.llm_provider

    suffix = Path(file.filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()

        llm = LLMFactory.create(provider)
        orch = Orchestrator(llm)
        report = await orch.review(file_path=tmp.name, competition=competition)

        db = SessionLocal()
        try:
            submission = Submission(
                student_name=student_name,
                competition=competition,
                competition_type=report.competition_type,
                filename=file.filename,
                word_count=report.meta.get("word_count", 0),
                status="done",
            )
            db.add(submission)
            db.flush()

            review = Review(
                submission_id=submission.id,
                model_provider=provider,
                total_score=report.total_score,
                score_rubric=report.scores.get("RubricParser"),
                score_structure=report.scores.get("StructureLogic"),
                score_argument=report.scores.get("ArgumentEvidence"),
                score_language=report.scores.get("LanguageStyle"),
                score_integrity=report.scores.get("AcademicIntegrity"),
                feedback_json=_convert_report_to_json(report),
                duration_seconds=report.meta.get("duration_seconds", 0),
            )
            db.add(review)
            db.commit()

            submission_id = submission.id
        finally:
            db.close()

        return JSONResponse(content={
            "submission_id": submission_id,
            "competition": competition,
            "competition_type": report.competition_type,
            "total_score": report.total_score,
            "scores": report.scores,
            "rubric": report.rubric,
            "structure": report.structure,
            "argument": report.argument,
            "language": report.language,
            "integrity": report.integrity,
            "meta": report.meta,
            "errors": report.errors,
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Review failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp.name).unlink(missing_ok=True)


@app.get("/api/v1/competitions")
async def list_competitions():
    registry = json.loads((Path(__file__).parent.parent / "configs" / "competition_registry.json").read_text(encoding="utf-8"))
    competitions = []
    for name, cfg in registry["competitions"].items():
        competitions.append({"name": name, "type": cfg["type"], "subtype": cfg.get("subtype")})
    return {"competitions": competitions}


@app.get("/api/v1/reviews")
async def list_reviews(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    db = SessionLocal()
    try:
        total = db.query(func.count(Submission.id)).scalar() or 0
        submissions = (
            db.query(Submission)
            .order_by(Submission.submitted_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for sub in submissions:
            latest_review = (
                db.query(Review)
                .filter(Review.submission_id == sub.id)
                .order_by(Review.created_at.desc())
                .first()
            )
            items.append({
                "submission_id": sub.id,
                "student_name": sub.student_name,
                "competition": sub.competition,
                "competition_type": sub.competition_type,
                "filename": sub.filename,
                "word_count": sub.word_count,
                "status": sub.status,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "total_score": latest_review.total_score if latest_review else None,
                "model_provider": latest_review.model_provider if latest_review else None,
                "reviewed_at": latest_review.created_at.isoformat() if latest_review and latest_review.created_at else None,
            })

        return {"reviews": items, "total": total, "offset": offset, "limit": limit}
    finally:
        db.close()


@app.get("/api/v1/reviews/{submission_id}")
async def get_review(submission_id: int):
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        reviews = (
            db.query(Review)
            .filter(Review.submission_id == submission_id)
            .order_by(Review.created_at.desc())
            .all()
        )

        review_items = []
        for rv in reviews:
            feedback = None
            if rv.feedback_json:
                try:
                    feedback = json.loads(rv.feedback_json)
                except json.JSONDecodeError:
                    feedback = rv.feedback_json

            review_items.append({
                "review_id": rv.id,
                "model_provider": rv.model_provider,
                "total_score": rv.total_score,
                "scores": {
                    "rubric": rv.score_rubric,
                    "structure": rv.score_structure,
                    "argument": rv.score_argument,
                    "language": rv.score_language,
                    "integrity": rv.score_integrity,
                },
                "feedback": feedback,
                "token_usage": rv.token_usage,
                "cost_usd": rv.cost_usd,
                "duration_seconds": rv.duration_seconds,
                "created_at": rv.created_at.isoformat() if rv.created_at else None,
            })

        return {
            "submission_id": submission.id,
            "student_name": submission.student_name,
            "competition": submission.competition,
            "competition_type": submission.competition_type,
            "filename": submission.filename,
            "word_count": submission.word_count,
            "status": submission.status,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "reviews": review_items,
        }
    finally:
        db.close()


@app.get("/api/v1/config/stats")
async def config_stats():
    configs_root = Path(__file__).parent.parent / "configs"

    def _count_json(dir_name: str) -> int:
        d = configs_root / dir_name
        if not d.exists():
            return 0
        return len(list(d.glob("*.json")))

    rubric_count = _count_json("rubrics")
    structure_count = _count_json("structure_schemas")
    evidence_count = _count_json("evidence_patterns")
    style_count = _count_json("style_guides")
    citation_count = _count_json("citation_rules")

    registry_path = configs_root / "competition_registry.json"
    competition_count = 0
    competition_types = set()
    competition_list = []
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for name, cfg in registry.get("competitions", {}).items():
            competition_count += 1
            competition_types.add(cfg["type"])
            competition_list.append({"name": name, "type": cfg["type"], "subtype": cfg.get("subtype")})

    db = SessionLocal()
    try:
        total_reviews = db.query(func.count(Submission.id)).scalar() or 0
        total_calibrations = db.query(func.count(CalibrationRecord.id)).scalar() or 0
        db_submissions = db.query(Submission).all()
        by_competition = {}
        for sub in db_submissions:
            by_competition[sub.competition] = by_competition.get(sub.competition, 0) + 1
    finally:
        db.close()

    sync_enabled = bool(settings.sync_server_url.strip())

    return {
        "competitions": {
            "total": competition_count,
            "types": sorted(competition_types),
            "list": sorted(competition_list, key=lambda x: x["name"]),
        },
        "configs": {
            "rubrics": rubric_count,
            "structure_schemas": structure_count,
            "evidence_patterns": evidence_count,
            "style_guides": style_count,
            "citation_rules": citation_count,
        },
        "db": {
            "total_submissions": total_reviews,
            "total_calibrations": total_calibrations,
            "by_competition": by_competition,
        },
        "sync": {
            "enabled": sync_enabled,
            "server_url": settings.sync_server_url if sync_enabled else "",
        },
    }


@app.post("/api/v1/sync/review")
async def sync_review(payload: dict):
    db = SessionLocal()
    try:
        instance_name = payload.get("instance_name", "unknown")
        raw_competition = payload.get("competition", "")
        record = CalibrationRecord(
            instance_name=instance_name,
            competition=normalize_competition_name(raw_competition),
            competition_type=payload.get("competition_type", ""),
            n_winners=0,
            n_losers=0,
            n_external=0,
            report_json=json.dumps(payload, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@app.post("/api/v1/sync/calibration")
async def sync_calibration(payload: dict):
    db = SessionLocal()
    try:
        raw_competition = payload.get("competition", "")
        record = CalibrationRecord(
            instance_name=payload.get("instance_name", "unknown"),
            competition=normalize_competition_name(raw_competition),
            competition_type=payload.get("competition_type", ""),
            n_winners=payload.get("n_winners", 0),
            n_losers=payload.get("n_losers", 0),
            n_external=payload.get("n_external", 0),
            report_json=json.dumps(payload, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}


@app.get("/api/v1/admin/dashboard")
async def admin_dashboard():
    db = SessionLocal()
    try:
        total_reviews = db.query(func.count(Submission.id)).scalar() or 0
        total_calibrations = db.query(func.count(CalibrationRecord.id)).scalar() or 0

        instances = set()
        db_subs = db.query(Submission).all()
        by_competition = {}
        by_instance = {}
        for sub in db_subs:
            by_competition[sub.competition] = by_competition.get(sub.competition, 0) + 1

        cals = db.query(CalibrationRecord).all()
        cal_by_competition = {}
        cal_by_instance = {}
        for cal in cals:
            instances.add(cal.instance_name)
            cal_by_competition[cal.competition] = cal_by_competition.get(cal.competition, 0) + 1
            cal_by_instance[cal.instance_name] = cal_by_instance.get(cal.instance_name, 0) + 1
            by_instance[cal.instance_name] = by_instance.get(cal.instance_name, 0)

        recent_cals = []
        for cal in sorted(cals, key=lambda c: c.created_at or datetime.min, reverse=True)[:20]:
            recent_cals.append({
                "id": cal.id,
                "instance": cal.instance_name,
                "competition": cal.competition,
                "winners": cal.n_winners,
                "losers": cal.n_losers,
                "created_at": cal.created_at.isoformat() if cal.created_at else None,
            })

        return {
            "summary": {
                "total_reviews": total_reviews,
                "total_calibrations": total_calibrations,
                "total_instances": len(instances),
                "instances": sorted(instances),
            },
            "reviews_by_competition": by_competition,
            "calibrations_by_competition": cal_by_competition,
            "calibrations_by_instance": cal_by_instance,
            "recent_calibrations": recent_cals,
        }
    finally:
        db.close()


@app.get("/api/v1/sync/configs")
async def sync_configs_download():
    files = {}
    for json_file in sorted(_CONFIGS_DIR.rglob("*.json")):
        rel = str(json_file.relative_to(_CONFIGS_DIR)).replace("\\", "/")
        files[rel] = json_file.read_text(encoding="utf-8")

    payload = json.dumps(files, ensure_ascii=False, sort_keys=True)
    config_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]

    return {
        "version": config_hash,
        "files": files,
    }
