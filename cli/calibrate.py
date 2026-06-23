"""
校准引擎 CLI 入口

用法:
    python cli/calibrate.py \\
        --competition ISEF \\
        --type research \\
        --winners ./data/calibration/winners/ \\
        --losers ./data/calibration/losers/ \\
        --external ./data/calibration/external/ \\
        --expert-docs ./data/expert_insights/ \\
        --output ./reports/calibration_isef_2026.md
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calibration.engine import run_calibration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _collect_files(dir_path: str) -> list[str]:
    p = Path(dir_path)
    if not p.is_dir():
        return []
    supported = {".txt", ".md", ".pdf", ".docx"}
    files = sorted(
        str(f) for f in p.iterdir()
        if f.suffix.lower() in supported and f.is_file()
    )
    return files


def main():
    parser = argparse.ArgumentParser(
        description="AcademicReviewer Calibration Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--competition", required=True, help="竞赛名称，如 ISEF")
    parser.add_argument("--type", required=True, dest="competition_type", help="竞赛类型，如 research")
    parser.add_argument("--winners", default="", help="我方获奖文章目录")
    parser.add_argument("--losers", default="", help="我方失败文章目录")
    parser.add_argument("--external", default=None, help="外部获奖文章目录（可选）")
    parser.add_argument("--expert-docs", default=None, help="教师经验文档目录（可选，.md格式）")
    parser.add_argument("--output", default=None, help="报告输出路径（可选，默认打印到 stdout）")

    args = parser.parse_args()

    winner_files = _collect_files(args.winners)
    loser_files = _collect_files(args.losers)
    external_files = _collect_files(args.external) if args.external else []
    expert_doc_files = _collect_files(args.expert_docs) if args.expert_docs else []

    if not winner_files:
        logger.warning(f"No winner files found in: {args.winners}")
    if not loser_files:
        logger.warning(f"No loser files found in: {args.losers}")

    if not (winner_files or loser_files or external_files or expert_doc_files):
        logger.error("No files found in any of the specified directories")
        sys.exit(1)

    logger.info(
        f"Calibration starting: W={len(winner_files)}, L={len(loser_files)}, Ext={len(external_files)}, ExpertDocs={len(expert_doc_files)}"
    )

    report, _expert_insights = run_calibration(
        competition=args.competition,
        competition_type=args.competition_type,
        winner_files=winner_files,
        loser_files=loser_files,
        external_winner_files=external_files if external_files else None,
        expert_doc_paths=expert_doc_files if expert_doc_files else None,
        output_report_path=args.output,
    )

    if not args.output:
        print(report)

    logger.info("Calibration complete.")


if __name__ == "__main__":
    main()
