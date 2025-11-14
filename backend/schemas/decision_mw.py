from __future__ import annotations

"""
Free Intelligence - Decision Middleware

Simple if/else rules engine applied on validated JSON Schema output.

Philosophy: Rules-on-schema, not multi-agent complexity.
Output: Domain events emitted based on conditions.

File: backend/decision_mw.py
Created: 2025-10-28
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionEvent:
    """Domain event emitted by decision middleware"""

    event: str
    priority: str
    metadata: Dict[str, Any]
    rule_name: str


class ConditionEvaluator:
    """
    Evaluate conditions against JSON data.

    Supports operators:
    - equals, not_equals
    - greater_than, less_than, gte, lte
    - contains, not_contains (string)
    - array_contains, array_not_empty, array_length_gte
    - is_null, is_not_null
    - and, or (nested conditions)
    - always (always true)
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    def evaluate(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """
        Evaluate condition against data.

        Args:
            condition: Condition definition from YAML
            data: JSON data to evaluate

        Returns:
            True if condition matches, False otherwise
        """
        operator = condition.get("operator")

        # Logical operators (nested conditions)
        if operator == "and":
            return self._eval_and(condition.get("conditions", []), data)
        elif operator == "or":
            return self._eval_or(condition.get("conditions", []), data)
        elif operator == "always":
            return True

        # Field-based operators
        field = condition.get("field")
        if not field:
            self.logger.error("CONDITION_MISSING_FIELD", condition=condition)
            return False

        value = self._get_field_value(data, field)
        expected = condition.get("value")

        # Evaluate operator
        if operator == "equals":
            return value == expected
        elif operator == "not_equals":
            return value != expected
        elif operator == "greater_than":
            return value is not None and value > expected
        elif operator == "less_than":
            return value is not None and value < expected
        elif operator == "gte":
            return value is not None and value >= expected
        elif operator == "lte":
            return value is not None and value <= expected
        elif operator == "contains":
            return value is not None and expected is not None and expected in str(value)
        elif operator == "not_contains":
            return value is not None and expected is not None and expected not in str(value)
        elif operator == "array_contains":
            return isinstance(value, list) and expected in value
        elif operator == "array_not_empty":
            return isinstance(value, list) and len(value) > 0
        elif operator == "array_length_gte":
            return isinstance(value, list) and expected is not None and len(value) >= expected
        elif operator == "is_null":
            return value is None
        elif operator == "is_not_null":
            return value is not None
        else:
            self.logger.error("UNKNOWN_OPERATOR", operator=operator)
            return False

    def _eval_and(self, conditions: list[dict], data: dict) -> bool:
        """Evaluate AND of multiple conditions"""
        return all(self.evaluate(cond, data) for cond in conditions)

    def _eval_or(self, conditions: list[dict], data: dict) -> bool:
        """Evaluate OR of multiple conditions"""
        return any(self.evaluate(cond, data) for cond in conditions)

    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """
        Get nested field value using dot notation.

        Examples:
            "urgency" -> data["urgency"]
            "demographics.age" -> data["demographics"]["age"]
            "medical_history.allergies" -> data["medical_history"]["allergies"]
        """
        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value


class DecisionMiddleware:
    """
    Decision middleware engine.

    Loads rules from YAML and applies them to validated JSON output.
    Emits domain events based on matching conditions.
    """

    def __init__(self, rules_path: str = "config/decision_rules.yaml"):
        """
        Initialize decision middleware.

        Args:
            rules_path: Path to decision rules YAML
        """
        self.rules_path = Path(rules_path)
        self.evaluator = ConditionEvaluator()
        self.logger = get_logger(__name__)

        # Load rules
        self.rules = self._load_rules()

        self.logger.info(
            "DECISION_MIDDLEWARE_INITIALIZED",
            rules_path=str(self.rules_path),
            presets=list(self.rules.keys()),
        )

    @lru_cache(maxsize=10)
    def _load_rules(self) -> dict[str, Any]:
        """
        Load decision rules from YAML.

        Returns:
            Dict of preset_id -> rules config

        Raises:
            FileNotFoundError: If rules file not found
            ValueError: If YAML is invalid
        """
        if not self.rules_path.exists():
            self.logger.error("RULES_FILE_NOT_FOUND", file_path=str(self.rules_path))
            raise FileNotFoundError(f"Rules file not found: {self.rules_path}")

        self.logger.info("RULES_LOADING_STARTED", file_path=str(self.rules_path))

        try:
            with open(self.rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Extract preset rules (skip metadata)
            rules = {
                key: value
                for key, value in data.items()
                if key not in ["version", "created_at", "description", "metadata"]
            }

            self.logger.info(
                "RULES_LOADED_SUCCESSFULLY", presets=list(rules.keys()), version=data.get("version")
            )

            return rules

        except Exception as e:
            self.logger.error("RULES_LOADING_FAILED", error=str(e))
            raise ValueError(f"Failed to load rules: {e}")

    def apply_rules(
        self, preset_id: str, data: Dict[str, Any], stop_on_first_match: bool = False
    ) -> list[DecisionEvent]:
        """
        Apply decision rules to validated JSON data.

        Args:
            preset_id: Preset identifier (e.g., "intake_coach")
            data: Validated JSON data
            stop_on_first_match: If True, stop after first matching rule

        Returns:
            List of DecisionEvent objects emitted

        Raises:
            ValueError: If preset_id not found in rules
        """
        if preset_id not in self.rules:
            self.logger.error("PRESET_NOT_FOUND_IN_RULES", preset_id=preset_id)
            raise ValueError(f"Preset {preset_id} not found in rules")

        preset_rules = self.rules[preset_id]
        rules_list = preset_rules.get("rules", [])

        self.logger.info(
            "RULES_APPLICATION_STARTED",
            preset_id=preset_id,
            rules_count=len(rules_list),
            stop_on_first_match=stop_on_first_match,
        )

        events = []

        for rule in rules_list:
            rule_name = rule.get("name", "unnamed_rule")
            condition = rule.get("condition")
            actions = rule.get("actions", [])

            # Evaluate condition
            try:
                matches = self.evaluator.evaluate(condition, data)
            except Exception as e:
                self.logger.error("CONDITION_EVALUATION_FAILED", rule_name=rule_name, error=str(e))
                continue

            if matches:
                self.logger.info("RULE_MATCHED", rule_name=rule_name, actions_count=len(actions))

                # Execute actions
                for action in actions:
                    if action.get("type") == "emit_event":
                        event = DecisionEvent(
                            event=action["event"],
                            priority=action.get("priority", "P4"),
                            metadata=action.get("metadata", {}),
                            rule_name=rule_name,
                        )
                        events.append(event)

                        self.logger.info(
                            "DECISION_EVENT_EMITTED",
                            event_name=event.event,
                            priority=event.priority,
                            rule_name=rule_name,
                        )

                    elif action.get("type") == "log":
                        log_level = action.get("level", "info")
                        message = action.get("message", "")
                        getattr(self.logger, log_level)(
                            "RULE_ACTION_LOG", rule_name=rule_name, message=message
                        )

                # Stop on first match if requested
                if stop_on_first_match:
                    break

        self.logger.info(
            "RULES_APPLICATION_COMPLETE", preset_id=preset_id, events_emitted=len(events)
        )

        return events

    def list_presets(self) -> list[str]:
        """List available preset IDs with rules"""
        return list(self.rules.keys())

    def get_preset_rules(self, preset_id: str) -> dict[str, Any]:
        """Get rules for a specific preset"""
        if preset_id not in self.rules:
            raise ValueError(f"Preset {preset_id} not found")
        return self.rules[preset_id]


# Global decision middleware instance
_decision_middleware: Optional[DecisionMiddleware] = None


def get_decision_middleware() -> DecisionMiddleware:
    """Get or create global decision middleware"""
    global _decision_middleware

    if _decision_middleware is None:
        _decision_middleware = DecisionMiddleware()

    return _decision_middleware


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for decision middleware"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Free Intelligence Decision Middleware CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # List command
    _list_parser = subparsers.add_parser("list", help="List available presets")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show rules for preset")
    show_parser.add_argument("preset_id", help="Preset ID")

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply rules to JSON data")
    apply_parser.add_argument("preset_id", help="Preset ID")
    apply_parser.add_argument("json_file", help="JSON file with data")
    apply_parser.add_argument(
        "--first-match", action="store_true", help="Stop on first matching rule"
    )

    args = parser.parse_args()

    mw = get_decision_middleware()

    if args.command == "list":
        presets = mw.list_presets()
        print("\n" + "=" * 70)
        print("📋 Available Presets")
        print("=" * 70)
        for preset_id in presets:
            rules = mw.get_preset_rules(preset_id)
            print(f"\n  {preset_id}")
            print(f"    Rules: {len(rules.get('rules', []))}")
            print(f"    Schema: {rules.get('schema', 'N/A')}")
        print("\n" + "=" * 70)

    elif args.command == "show":
        rules = mw.get_preset_rules(args.preset_id)
        print("\n" + "=" * 70)
        print(f"📋 Rules for: {args.preset_id}")
        print("=" * 70)
        print(f"\nSchema: {rules.get('schema')}")
        print(f"\nRules ({len(rules.get('rules', []))}):")
        for i, rule in enumerate(rules.get("rules", []), 1):
            print(f"\n  {i}. {rule.get('name')}")
            print(f"     Description: {rule.get('description')}")
            print(f"     Actions: {len(rule.get('actions', []))}")
        print("\n" + "=" * 70)

    elif args.command == "apply":
        with open(args.json_file) as f:
            data = json.load(f)

        events = mw.apply_rules(args.preset_id, data, stop_on_first_match=args.first_match)

        print("\n" + "=" * 70)
        print(f"🎯 Decision Events Emitted: {len(events)}")
        print("=" * 70)

        for event in events:
            print(f"\n  Event: {event.event}")
            print(f"  Priority: {event.priority}")
            print(f"  Rule: {event.rule_name}")
            print(f"  Metadata: {event.metadata}")

        print("\n" + "=" * 70)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
