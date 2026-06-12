import json
import hashlib
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Header, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func

from app.config import settings, ensure_dirs, normalize_competition_name
from app.database import init_db, SessionLocal
from app.llm.base import LLMFactory
from app.orchestrator import Orchestrator, ReviewReport
from app.models.submission import Submission, Review, CalibrationRecord, TeacherFeedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ensure_dirs()
init_db()

app = FastAPI(title="AcademicReviewer", version="0.6.0")

SUBMISSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "submissions"
_CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

# === Security settings ===
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
_ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


async def _verify_api_token(authorization: str = Header(default=None)):
    """Simple Bearer Token auth. If API_TOKEN is not set, allow all requests."""
    if not settings.api_token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")
    token = authorization[7:]
    if token != settings.api_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")


def _validate_file(suffix: str, size: int) -> None:
    """Validate file extension and size. Raises HTTPException on failure."""
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file format: {suffix}. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}")
    if size > _MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large ({size / 1024 / 1024:.1f}MB). Max allowed: {_MAX_FILE_SIZE / 1024 / 1024:.0f}MB")


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
    token_check: None = Depends(_verify_api_token),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = Path(file.filename).suffix.lower()

    # Read file content for size check and processing
    contents = await file.read(_MAX_FILE_SIZE + 1)
    _validate_file(suffix, len(contents))

    provider = model_provider or settings.llm_provider
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(contents)
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


# ── Teacher Feedback API (Phase 3: 反馈闭环) ──


@app.post("/api/v1/feedback")
async def submit_teacher_feedback(payload: dict, token_check: None = Depends(_verify_api_token)):
    """老师对 AI 评审结果逐条审核并提交反馈。

    Payload:
        review_id: int
        teacher_id: str
        corrections: [
            {
                agent_name: str (A2/A3/A4/A5),
                item_path: str (e.g. "section_issues[0]"),
                item_type: str (e.g. "section_issue"),
                ai_content: str,
                ai_substitutability: str (FULL/REVIEW/ESCALATE),
                teacher_action: str (CONFIRM/OVERRIDE/REFINE),
                teacher_note: str (optional),
            }
        ]
    """
    review_id = payload.get("review_id")
    teacher_id = payload.get("teacher_id", "")
    corrections = payload.get("corrections", [])

    if not review_id:
        raise HTTPException(status_code=400, detail="Missing review_id")
    if not corrections:
        raise HTTPException(status_code=400, detail="No corrections provided")

    db = SessionLocal()
    try:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        saved = 0
        for corr in corrections:
            fb = TeacherFeedback(
                review_id=review_id,
                teacher_id=teacher_id,
                agent_name=corr.get("agent_name", ""),
                item_path=corr.get("item_path", ""),
                item_type=corr.get("item_type", ""),
                ai_content=corr.get("ai_content", ""),
                ai_substitutability=corr.get("ai_substitutability", "REVIEW"),
                teacher_action=corr.get("teacher_action", "CONFIRM"),
                teacher_note=corr.get("teacher_note", ""),
            )
            db.add(fb)
            saved += 1

        db.commit()
        return {"status": "ok", "saved": saved}
    finally:
        db.close()


@app.get("/api/v1/reviews/{submission_id}/feedback")
async def get_review_feedback(submission_id: int):
    """获取某个 submission 的全部 feedback 记录。"""
    db = SessionLocal()
    try:
        reviews = (
            db.query(Review)
            .filter(Review.submission_id == submission_id)
            .order_by(Review.created_at.desc())
            .all()
        )
        if not reviews:
            raise HTTPException(status_code=404, detail="Submission not found")

        all_feedback = []
        for rv in reviews:
            fbs = (
                db.query(TeacherFeedback)
                .filter(TeacherFeedback.review_id == rv.id)
                .order_by(TeacherFeedback.created_at.asc())
                .all()
            )
            for fb in fbs:
                all_feedback.append({
                    "feedback_id": fb.id,
                    "review_id": fb.review_id,
                    "teacher_id": fb.teacher_id,
                    "agent_name": fb.agent_name,
                    "item_path": fb.item_path,
                    "item_type": fb.item_type,
                    "ai_content": fb.ai_content,
                    "ai_substitutability": fb.ai_substitutability,
                    "teacher_action": fb.teacher_action,
                    "teacher_note": fb.teacher_note,
                    "created_at": fb.created_at.isoformat() if fb.created_at else None,
                })

        return {
            "submission_id": submission_id,
            "feedback_count": len(all_feedback),
            "feedback": all_feedback,
        }
    finally:
        db.close()


@app.get("/api/v1/feedback/stats")
async def feedback_stats(token_check: None = Depends(_verify_api_token)):
    """置信度校准统计：按 Agent/竞赛类型统计 AI 信心 vs 老师确认率。"""
    db = SessionLocal()
    try:
        all_fb = db.query(TeacherFeedback).all()

        by_agent = {}
        by_substitutability = {}
        total_confirmed = 0
        total_overridden = 0
        total_refined = 0

        for fb in all_fb:
            agent = fb.agent_name or "unknown"
            if agent not in by_agent:
                by_agent[agent] = {"total": 0, "confirmed": 0, "overridden": 0, "refined": 0}
            by_agent[agent]["total"] += 1
            if fb.teacher_action == "CONFIRM":
                by_agent[agent]["confirmed"] += 1
                total_confirmed += 1
            elif fb.teacher_action == "OVERRIDE":
                by_agent[agent]["overridden"] += 1
                total_overridden += 1
            elif fb.teacher_action == "REFINE":
                by_agent[agent]["refined"] += 1
                total_refined += 1

            sub = fb.ai_substitutability or "REVIEW"
            if sub not in by_substitutability:
                by_substitutability[sub] = {"total": 0, "confirmed": 0, "overridden": 0, "refined": 0}
            by_substitutability[sub]["total"] += 1
            if fb.teacher_action == "CONFIRM":
                by_substitutability[sub]["confirmed"] += 1
            elif fb.teacher_action == "OVERRIDE":
                by_substitutability[sub]["overridden"] += 1
            elif fb.teacher_action == "REFINE":
                by_substitutability[sub]["refined"] += 1

        # Build per-agent summary with confirmation rates
        agent_summary = {}
        for agent, stats in sorted(by_agent.items()):
            t = stats["total"]
            agent_summary[agent] = {
                "total": t,
                "confirmed": stats["confirmed"],
                "overridden": stats["overridden"],
                "refined": stats["refined"],
                "confirmation_rate": round(stats["confirmed"] / t, 3) if t > 0 else 0,
            }

        sub_summary = {}
        for sub, stats in sorted(by_substitutability.items()):
            t = stats["total"]
            sub_summary[sub] = {
                "total": t,
                "confirmed": stats["confirmed"],
                "overridden": stats["overridden"],
                "refined": stats["refined"],
                "confirmation_rate": round(stats["confirmed"] / t, 3) if t > 0 else 0,
            }

        total = len(all_fb)
        return {
            "total_feedback": total,
            "total_confirmed": total_confirmed,
            "total_overridden": total_overridden,
            "total_refined": total_refined,
            "overall_confirmation_rate": round(total_confirmed / total, 3) if total > 0 else 0,
            "by_agent": agent_summary,
            "by_substitutability": sub_summary,
        }
    finally:
        db.close()


@app.get("/api/v1/feedback/suggestions")
async def feedback_suggestions(threshold: int = 3, token_check: None = Depends(_verify_api_token)):
    """基于反馈数据，自动检测需要修正的知识卡条目。

    当某个 Agent 的特定 item_type 被老师反复 override/refine 超过 threshold 次时，
    说明 AI 在该领域判断不准，建议补充或修正对应的知识卡条目。

    Args:
        threshold: 触发建议的最低 override/refine 次数（默认 3）
    """
    db = SessionLocal()
    try:
        all_fb = db.query(TeacherFeedback).filter(
            TeacherFeedback.teacher_action.in_(["OVERRIDE", "REFINE"])
        ).all()

        # Aggregate by agent_name + item_type
        from collections import Counter
        counter = Counter()
        pattern_map = {}  # (agent, item_type) -> list of teacher_notes

        for fb in all_fb:
            key = (fb.agent_name or "unknown", fb.item_type or "unknown")
            counter[key] += 1
            if key not in pattern_map:
                pattern_map[key] = []
            if fb.teacher_note:
                pattern_map[key].append(fb.teacher_note)

        suggestions = []
        for (agent, item_type), count in counter.most_common():
            if count >= threshold:
                notes = pattern_map.get((agent, item_type), [])
                # Suggest what kind of knowledge card update is needed
                suggestion = {
                    "agent_name": agent,
                    "item_type": item_type,
                    "override_count": count,
                    "recommended_action": f"建议在 {agent} 的知识卡中添加或修正关于 '{item_type}' 的条目",
                    "sample_teacher_notes": notes[-5:],  # last 5 notes
                    "knowledge_card_type": _suggest_card_type(item_type),
                }
                suggestions.append(suggestion)

        return {
            "total_override_events": len(all_fb),
            "threshold": threshold,
            "suggestions": suggestions,
            "note": "建议定期（每学期）检查此列表，将高频被纠正的模式写入 data/expert_insights/ 目录下的专家经验文档。",
        }
    finally:
        db.close()


def _suggest_card_type(item_type: str) -> str:
    """根据 item_type 建议对应的知识卡类型。"""
    mapping = {
        "section_issue": "fatal_defect 或 pattern",
        "logic_issue": "pitfall",
        "claim": "pattern 或 benchmark",
        "logical_fallacy": "pitfall",
        "rewrite": "pattern",
        "suggestion": "pattern 或 signal",
        "citation_issue": "fatal_defect 或 rubric",
        "originality_flag": "fatal_defect",
    }
    return mapping.get(item_type, "pattern")


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
async def sync_review(payload: dict, token_check: None = Depends(_verify_api_token)):
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
async def sync_calibration(payload: dict, token_check: None = Depends(_verify_api_token)):
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
async def admin_dashboard(token_check: None = Depends(_verify_api_token)):
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
async def sync_configs_download(token_check: None = Depends(_verify_api_token)):
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


@app.get("/api/v1/admin/competitions")
async def admin_competitions_list(token_check: None = Depends(_verify_api_token)):
    import copy
    registry_path = _CONFIGS_DIR / "competition_registry.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    result = []
    for name, cfg in data.get("competitions", {}).items():
        entry = copy.deepcopy(cfg)
        entry["_name"] = name
        result.append(entry)
    result.sort(key=lambda x: x["_name"])
    return {"competitions": result, "types": data.get("competition_types", {})}


@app.post("/api/v1/admin/competitions")
async def admin_competitions_save(payload: dict, token_check: None = Depends(_verify_api_token)):
    registry_path = _CONFIGS_DIR / "competition_registry.json"
    current = json.loads(registry_path.read_text(encoding="utf-8"))

    competitions = {}
    for entry in payload.get("competitions", []):
        name = entry.pop("_name", "").strip()
        if not name:
            continue
        aliases = []
        for a in entry.get("aliases", []):
            a = a.strip()
            if a and a.lower() != name.lower():
                aliases.append(a)
        entry["aliases"] = aliases
        competitions[name] = entry

    current["competitions"] = competitions
    if "types" in payload:
        current["competition_types"] = payload["types"]

    backup = registry_path.with_suffix(".json.bak")
    if registry_path.exists():
        backup.write_text(registry_path.read_text(encoding="utf-8"))

    registry_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok", "count": len(competitions)}
