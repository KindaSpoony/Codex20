"""
Orchestrator script for the Codex20 OSINT pipeline.

This script glues together the pipeline modules defined in the repository.  It
loads a playbook configuration, executes each stage of the OSINT workflow
(collecting data, evaluating source credibility, applying heuristics,
performing threat/temporal analysis, and triangulating findings) and
produces both intermediate artifacts and a final consolidated report.

The orchestrator uses structured logging: JSON lines are written to
`results/pipeline.log` while human-readable summaries are printed to the
console.  Critical configuration or file-write failures will halt execution,
while non-fatal collection or network errors are logged and skipped.
"""

import json
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Import pipeline classes.  Adjust the module name if necessary.
from osint_pipeline_modules import (
    PlaybookParser,
    Collector,
    SourceEvaluator,
    HeuristicProcessor,
    ThreatTemporalAnalyzer,
    TriangulatorReporter,
)


def setup_logging(log_file: Path) -> logging.Logger:
    """Configure a logger that writes JSON lines to file and summaries to console."""
    logger = logging.getLogger("osint_pipeline")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)

        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_record = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "message": record.getMessage(),
                }
                return json.dumps(log_record)

        fh.setFormatter(JsonFormatter())
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(ch)
    return logger


def save_json(data: Any, filepath: Path) -> None:
    """Write data to a JSON file with pretty indentation."""
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main(playbook_path: str = "OSINT_playbook.yaml") -> None:
    """Execute the OSINT pipeline using the specified playbook."""
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    log_file = results_dir / "pipeline.log"
    logger = setup_logging(log_file)
    logger.info("OSINT pipeline started")

    # Load playbook
    try:
        parser = PlaybookParser(playbook_path)
        playbook: Dict[str, Any] = parser.parse_playbook()
        logger.info(f"Loaded playbook from {playbook_path}")
    except FileNotFoundError as exc:
        logger.error(f"Playbook file not found: {playbook_path}")
        raise exc
    except yaml.YAMLError as exc:
        logger.error(f"Failed to parse YAML playbook: {exc}")
        raise exc

    tools_config: Dict[str, Any] = playbook.get("tools", {})
    mission_config: Dict[str, Any] = playbook.get("mission", {})
    tiers_config: Dict[str, Any] = playbook.get("source_tiers", {})
    heuristics_config: Dict[str, Any] = playbook.get("heuristics", {})
    queries: List[str] = mission_config.get("queries", []) or []
    if not queries:
        logger.warning("No queries defined in playbook mission; pipeline will exit.")
        return

    # Initialize modules
    collector = Collector(tools_config)
    evaluator = SourceEvaluator(tiers_config)
    heuristic_processor = HeuristicProcessor(heuristics_config)
    threat_analyzer = ThreatTemporalAnalyzer()
    reporter = TriangulatorReporter()

    # Stage 1: Data collection
    logger.info(f"Collecting data for {len(queries)} queries…")
    collected = collector.collect_data(queries)
    save_json(collected, results_dir / "collected.json")
    logger.info(f"Collected {len(collected)} items")

    # Stage 2: Source evaluation
    logger.info("Evaluating source credibility…")
    evaluated = evaluator.evaluate_sources(collected)
    save_json(evaluated, results_dir / "evaluated.json")
    logger.info(f"Evaluated {len(evaluated)} unique sources")

    # Stage 3: Heuristic processing
    logger.info("Applying heuristic analysis…")
    analyzed = heuristic_processor.analyze_data(evaluated)
    save_json(analyzed, results_dir / "analyzed.json")
    logger.info("Heuristic processing completed")

    # Stage 4: Threat and temporal analysis
    logger.info("Performing threat and temporal analysis…")
    threats = threat_analyzer.analyze_threats(analyzed)
    save_json(threats, results_dir / "threats.json")
    logger.info("Threat/temporal analysis completed")

    # Stage 5: Triangulation and final reporting
    logger.info("Triangulating findings and generating final report…")
    final_report = reporter.triangulate_and_report(threats)
    reporter.generate_report(final_report, str(results_dir / "final_report.json"))
    logger.info("Final report generated")
    logger.info("OSINT pipeline completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Pipeline execution failed")
        raise
