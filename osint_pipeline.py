"""OSINT Pipeline Modules.

This module implements a lightweight pipeline for working with
OSINT playbooks. It parses a YAML configuration, collects data
via simple HTTP requests, evaluates source credibility, performs
basic heuristic analysis, checks for threat indicators, and
produces a consolidated JSON report.

The implementation is intentionally minimal and focuses on clarity
rather than production-ready features. Network requests are made
with the `requests` package and are rate limited to avoid overloading
remote services.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests
import yaml


class PlaybookParser:
    """Load a YAML playbook from disk."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def parse_playbook(self) -> Dict[str, Any]:
        with open(self.filepath, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)


@dataclass
class Tool:
    name: str
    endpoint: str


class Collector:
    """Simple HTTP collector."""

    def __init__(self, tools: Iterable[Tool], rate_limit: float = 1.0) -> None:
        self.tools = list(tools)
        self.rate_limit = max(rate_limit, 0.0)
        self.headers = {"User-Agent": "OSINT-Collector/1.0"}

    def collect_data(self, queries: Iterable[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for query in queries:
            for tool in self.tools:
                url = f"{tool.endpoint}?q={query}"
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        results.append(
                            {
                                "query": query,
                                "url": response.url,
                                "timestamp": datetime.utcnow().isoformat(),
                                "content": response.text,
                            }
                        )
                except requests.RequestException:
                    # Skip failed requests but continue with others
                    pass
                time.sleep(self.rate_limit)
        return results


class SourceEvaluator:
    """Assign credibility to collected items based on source tiers."""

    def __init__(self, tiers: Dict[str, Dict[str, Any]]) -> None:
        self.tiers = tiers

    def evaluate_sources(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        evaluated: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()
        for item in items:
            tier = self.get_source_tier(item["url"])
            if tier and item["url"] not in seen_urls:
                item["tier"] = tier["name"]
                item["credibility"] = tier.get("credibility_weight", 0)
                evaluated.append(item)
                seen_urls.add(item["url"])
        return evaluated

    def get_source_tier(self, url: str) -> Optional[Dict[str, Any]]:
        domain = urlparse(url).netloc
        for name, tier in self.tiers.items():
            domains = tier.get("domains", [])
            if any(d in domain for d in domains):
                tier = dict(tier)
                tier["name"] = name
                return tier
        return None


class HeuristicProcessor:
    """Detect simple anomalies and hypotheses."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    def analyze_data(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        analysed: List[Dict[str, Any]] = []
        for item in items:
            anomalies = self._detect_anomalies(item.get("content", ""))
            hypotheses = self._generate_hypotheses(item.get("content", ""))
            item.update({"anomalies": anomalies, "hypotheses": hypotheses})
            analysed.append(item)
        return analysed

    def _detect_anomalies(self, content: str) -> List[str]:
        patterns = self.config.get("anomaly_patterns", [])
        return [p for p in patterns if p in content]

    def _generate_hypotheses(self, content: str) -> List[str]:
        result: List[str] = []
        for hyp in self.config.get("hypothesis_templates", []):
            if hyp.get("keyword") in content:
                result.append(hyp.get("description", ""))
        return result


class ThreatTemporalAnalyzer:
    """Identify threat indicators and temporal inconsistencies."""

    def analyze_threats(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        analysed: List[Dict[str, Any]] = []
        for item in items:
            content = item.get("content", "")
            threats = [s for s in ["malicious", "disinformation", "cyber-threat"] if s in content]
            item["threats"] = threats
            item["temporal_consistency"] = self._check_temporal(content)
            analysed.append(item)
        return analysed

    def _check_temporal(self, content: str) -> str:
        return "inconsistent" if "2022" in content and "2024" in content else "consistent"


class TriangulatorReporter:
    """Aggregate items and output a JSON report."""

    def triangulate_and_report(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        grouped: defaultdict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in items:
            grouped[item["query"]].append(item)

        final: Dict[str, Any] = {}
        for query, group in grouped.items():
            if len(group) < 2:
                continue
            confidence = sum(i.get("credibility", 0) for i in group) / len(group)
            discrepancies = len({i.get("content") for i in group}) > 1
            final[query] = {
                "sources": [
                    {"url": i["url"], "credibility": i.get("credibility", 0)} for i in group
                ],
                "confidence_score": confidence,
                "discrepancies": discrepancies,
            }
        return final

    def generate_report(self, report: Dict[str, Any], filename: str = "OSINT_Report.json") -> None:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=2)


if __name__ == "__main__":
    parser = PlaybookParser("OSINT_playbook.yaml")
    playbook = parser.parse_playbook()

    tool_cfg = playbook.get("tools", {}).get("recommended", [])
    tools = [Tool(name=t.get("name", "tool"), endpoint=t.get("endpoint", "")) for t in tool_cfg]

    collector = Collector(tools)
    queries = playbook.get("mission", {}).get("queries", [])
    collected = collector.collect_data(queries)

    evaluator = SourceEvaluator(playbook.get("source_tiers", {}))
    evaluated = evaluator.evaluate_sources(collected)

    heuristics = playbook.get("heuristics", {})
    processor = HeuristicProcessor(heuristics)
    analysed = processor.analyze_data(evaluated)

    threat_analyzer = ThreatTemporalAnalyzer()
    threats = threat_analyzer.analyze_threats(analysed)

    reporter = TriangulatorReporter()
    report = reporter.triangulate_and_report(threats)
    reporter.generate_report(report)

    print("OSINT Pipeline execution completed.")
