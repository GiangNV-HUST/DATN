"""
Model Usage Tracker
Track usage, costs, performance metrics cho đa model system
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict


@dataclass
class UsageStats:
    """Statistics cho 1 model"""
    model_name: str
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    error_count: int = 0
    task_distribution: Dict[str, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        """Average latency"""
        return self.total_latency_ms / self.total_requests if self.total_requests > 0 else 0

    @property
    def avg_cost_per_request(self) -> float:
        """Average cost per request"""
        return self.total_cost / self.total_requests if self.total_requests > 0 else 0

    @property
    def error_rate(self) -> float:
        """Error rate (%)"""
        return (self.error_count / self.total_requests * 100) if self.total_requests > 0 else 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "model_name": self.model_name,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": round(self.total_cost, 6),
            "avg_cost_per_request": round(self.avg_cost_per_request, 6),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 2),
            "task_distribution": self.task_distribution
        }


class ModelUsageTracker:
    """
    Track model usage, costs, và performance

    Features:
    - Per-model statistics
    - Task distribution tracking
    - Cost monitoring với alerts
    - Performance metrics
    - Export reports
    """

    def __init__(self, cost_alert_threshold: float = 10.0):
        """
        Initialize tracker

        Args:
            cost_alert_threshold: Alert khi tổng cost vượt ngưỡng này (USD)
        """
        self.cost_alert_threshold = cost_alert_threshold
        self.stats: Dict[str, UsageStats] = {}
        self.session_start = datetime.now()
        self.alerts_triggered = []

    def track_usage(
        self,
        model_name: str,
        task_type: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: float,
        error: bool = False
    ):
        """
        Track single model usage

        Args:
            model_name: Model name
            task_type: Task type (optional)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
            latency_ms: Latency in milliseconds
            error: Whether request errored
        """
        # Get or create stats
        if model_name not in self.stats:
            self.stats[model_name] = UsageStats(model_name=model_name)

        stats = self.stats[model_name]

        # Update stats
        stats.total_requests += 1
        stats.total_input_tokens += input_tokens
        stats.total_output_tokens += output_tokens
        stats.total_cost += cost
        stats.total_latency_ms += latency_ms

        if error:
            stats.error_count += 1

        # Track task distribution
        if task_type:
            stats.task_distribution[task_type] = stats.task_distribution.get(task_type, 0) + 1

        # Check cost alert
        total_cost = sum(s.total_cost for s in self.stats.values())
        if total_cost >= self.cost_alert_threshold:
            self._trigger_cost_alert(total_cost)

    def _trigger_cost_alert(self, total_cost: float):
        """Trigger cost alert"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "message": f"⚠️ Cost threshold exceeded: ${total_cost:.2f} >= ${self.cost_alert_threshold}",
            "total_cost": total_cost,
            "threshold": self.cost_alert_threshold
        }
        self.alerts_triggered.append(alert)
        print(alert["message"])

    def get_model_stats(self, model_name: str) -> Optional[UsageStats]:
        """Get stats cho 1 model"""
        return self.stats.get(model_name)

    def get_all_stats(self) -> Dict[str, UsageStats]:
        """Get stats cho tất cả models"""
        return self.stats

    def get_summary(self) -> Dict:
        """
        Get tổng hợp summary

        Returns:
            Dict với tổng hợp stats
        """
        total_requests = sum(s.total_requests for s in self.stats.values())
        total_cost = sum(s.total_cost for s in self.stats.values())
        total_errors = sum(s.error_count for s in self.stats.values())

        # Model distribution
        model_distribution = {
            name: {
                "requests": stats.total_requests,
                "percentage": (stats.total_requests / total_requests * 100) if total_requests > 0 else 0,
                "cost": stats.total_cost,
                "cost_percentage": (stats.total_cost / total_cost * 100) if total_cost > 0 else 0
            }
            for name, stats in self.stats.items()
        }

        # Task distribution (aggregated across all models)
        task_distribution = defaultdict(int)
        for stats in self.stats.values():
            for task, count in stats.task_distribution.items():
                task_distribution[task] += count

        session_duration = datetime.now() - self.session_start

        return {
            "session_start": self.session_start.isoformat(),
            "session_duration_minutes": session_duration.total_seconds() / 60,
            "total_requests": total_requests,
            "total_cost": round(total_cost, 6),
            "total_errors": total_errors,
            "error_rate": round((total_errors / total_requests * 100) if total_requests > 0 else 0, 2),
            "model_distribution": model_distribution,
            "task_distribution": dict(task_distribution),
            "cost_alerts_triggered": len(self.alerts_triggered),
            "models_used": list(self.stats.keys())
        }

    def get_cost_breakdown(self) -> Dict:
        """
        Get chi tiết cost breakdown

        Returns:
            Dict với cost breakdown by model và task
        """
        breakdown = {}

        for model_name, stats in self.stats.items():
            breakdown[model_name] = {
                "total_cost": round(stats.total_cost, 6),
                "requests": stats.total_requests,
                "avg_cost_per_request": round(stats.avg_cost_per_request, 6),
                "by_task": {}
            }

            # Estimate cost per task (rough approximation)
            total_task_count = sum(stats.task_distribution.values())
            if total_task_count > 0:
                for task, count in stats.task_distribution.items():
                    task_cost = (count / total_task_count) * stats.total_cost
                    breakdown[model_name]["by_task"][task] = {
                        "requests": count,
                        "estimated_cost": round(task_cost, 6)
                    }

        return breakdown

    def get_performance_metrics(self) -> Dict:
        """
        Get performance metrics

        Returns:
            Dict với latency và performance stats
        """
        metrics = {}

        for model_name, stats in self.stats.items():
            metrics[model_name] = {
                "avg_latency_ms": round(stats.avg_latency_ms, 2),
                "total_requests": stats.total_requests,
                "error_count": stats.error_count,
                "error_rate": round(stats.error_rate, 2),
                "tokens_per_second": round(
                    (stats.total_input_tokens + stats.total_output_tokens) / (stats.total_latency_ms / 1000)
                    if stats.total_latency_ms > 0 else 0,
                    2
                )
            }

        return metrics

    def export_report(self, filepath: str):
        """
        Export full report to JSON

        Args:
            filepath: Output file path
        """
        report = {
            "summary": self.get_summary(),
            "cost_breakdown": self.get_cost_breakdown(),
            "performance_metrics": self.get_performance_metrics(),
            "per_model_stats": {
                name: stats.to_dict()
                for name, stats in self.stats.items()
            },
            "alerts": self.alerts_triggered
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ Report exported to: {filepath}")

    def print_summary(self):
        """Print formatted summary to console"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("📊 MODEL USAGE SUMMARY")
        print("=" * 60)

        print(f"\n⏱️ Session Duration: {summary['session_duration_minutes']:.1f} minutes")
        print(f"📝 Total Requests: {summary['total_requests']}")
        print(f"💰 Total Cost: ${summary['total_cost']:.6f}")
        print(f"❌ Error Rate: {summary['error_rate']:.2f}%")

        print("\n🤖 Model Distribution:")
        for model, stats in summary['model_distribution'].items():
            print(f"   {model}:")
            print(f"      Requests: {stats['requests']} ({stats['percentage']:.1f}%)")
            print(f"      Cost: ${stats['cost']:.6f} ({stats['cost_percentage']:.1f}%)")

        print("\n📋 Task Distribution:")
        for task, count in summary['task_distribution'].items():
            percentage = (count / summary['total_requests'] * 100) if summary['total_requests'] > 0 else 0
            print(f"   {task}: {count} ({percentage:.1f}%)")

        if summary['cost_alerts_triggered'] > 0:
            print(f"\n⚠️ Cost Alerts Triggered: {summary['cost_alerts_triggered']}")

        print("=" * 60)

    def reset(self):
        """Reset all stats"""
        self.stats.clear()
        self.session_start = datetime.now()
        self.alerts_triggered.clear()
        print("✅ Usage tracker reset")


# Global singleton instance
_global_tracker = None


def get_usage_tracker() -> ModelUsageTracker:
    """Get global usage tracker instance"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ModelUsageTracker()
    return _global_tracker


# Example usage
if __name__ == "__main__":
    tracker = ModelUsageTracker(cost_alert_threshold=1.0)

    # Simulate usage
    tracker.track_usage("gemini-flash", "data_query", 100, 50, 0.000015, 50)
    tracker.track_usage("gemini-flash", "crud", 80, 40, 0.000012, 45)
    tracker.track_usage("gemini-pro", "screening", 500, 300, 0.00028, 120)
    tracker.track_usage("claude-sonnet", "analysis", 800, 1200, 0.0204, 350)
    tracker.track_usage("gpt-4o", "advisory", 1000, 1500, 0.0175, 450)

    # Print summary
    tracker.print_summary()

    # Export report
    tracker.export_report("usage_report.json")
