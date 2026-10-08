"""SQLite assembly of structured Card Battler mechanic graphs."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict

from comfyreview.application.card_battler_materialization import (
    MechanicBranchConditionGroupLink,
    MechanicBranchDefinition,
    MechanicConditionDefinition,
    MechanicConditionGroupDefinition,
    MechanicCostDefinition,
    MechanicParameterDefinition,
    MechanicParameterEnumValue,
    MechanicStepDefinition,
    MechanicStructureDefinition,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)


class _SqliteCardMechanicStructureReader:
    """Assemble ID-free mechanic graphs from normalized model facts."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def read(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, MechanicStructureDefinition]:
        mechanic_ids = tuple(
            int(row["id"])
            for row in connection.execute(
                """
                SELECT id FROM mechanic_templates
                WHERE ruleset_id = ? AND active = 1
                ORDER BY key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
        )
        _conditions, groups = self._condition_groups(connection, ruleset_id)
        steps = self._steps(connection, ruleset_id)
        links = self._branch_links(connection, ruleset_id)
        branches = self._branches(connection, ruleset_id, steps, links)
        costs = self._costs(connection, ruleset_id)
        parameters = self._parameters(connection, ruleset_id)
        empty_groups: tuple[MechanicConditionGroupDefinition, ...] = ()
        empty_branches: tuple[MechanicBranchDefinition, ...] = ()
        empty_costs: tuple[MechanicCostDefinition, ...] = ()
        empty_parameters: tuple[MechanicParameterDefinition, ...] = ()
        return {
            mechanic_id: MechanicStructureDefinition(
                branches=tuple(branches.get(mechanic_id, empty_branches)),
                condition_groups=tuple(groups.get(mechanic_id, empty_groups)),
                costs=tuple(costs.get(mechanic_id, empty_costs)),
                parameters=tuple(
                    parameters.get(mechanic_id, empty_parameters)
                ),
            )
            for mechanic_id in mechanic_ids
        }

    def _condition_groups(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> tuple[
        dict[int, list[MechanicConditionDefinition]],
        dict[int, list[MechanicConditionGroupDefinition]],
    ]:
        condition_rows = connection.execute(
            """
            SELECT conditions.condition_group_id, conditions.condition_order,
                   condition_types.key AS condition_type_key,
                   condition_types.ruleset_id AS condition_ruleset_id,
                   condition_types.active AS condition_active,
                   targets.key AS target_type_key,
                   targets.ruleset_id AS target_ruleset_id,
                   targets.active AS target_active,
                   conditions.comparator, conditions.value_int,
                   conditions.value_text, conditions.negated,
                   statuses.key AS status_type_key,
                   statuses.ruleset_id AS status_ruleset_id,
                   statuses.active AS status_active
            FROM mechanic_conditions AS conditions
            JOIN mechanic_condition_groups AS groups
              ON groups.id = conditions.condition_group_id
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = groups.mechanic_template_id
            JOIN condition_types
              ON condition_types.id = conditions.condition_type_id
            LEFT JOIN target_types AS targets
              ON targets.id = conditions.target_type_id
            LEFT JOIN status_types AS statuses
              ON statuses.id = conditions.status_type_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, groups.group_order,
                     conditions.condition_order
            """,
            (ruleset_id,),
        ).fetchall()
        conditions_by_group: dict[int, list[MechanicConditionDefinition]] = (
            defaultdict(list)
        )
        for row in condition_rows:
            self._validate_lookup(row, "condition", ruleset_id)
            self._validate_optional_lookup(row, "target", ruleset_id)
            self._validate_optional_lookup(row, "status", ruleset_id)
            conditions_by_group[int(row["condition_group_id"])].append(
                MechanicConditionDefinition(
                    order=int(row["condition_order"]),
                    condition_type_key=str(row["condition_type_key"]),
                    target_type_key=self._optional_text(
                        row["target_type_key"]
                    ),
                    comparator=self._optional_text(row["comparator"]),
                    value_int=self._optional_int(row["value_int"]),
                    value_text=self._optional_text(row["value_text"]),
                    negated=bool(row["negated"]),
                    status_type_key=self._optional_text(
                        row["status_type_key"]
                    ),
                )
            )
        group_rows = connection.execute(
            """
            SELECT groups.id, groups.mechanic_template_id,
                   groups.group_order, groups.operator,
                   groups.join_with_previous, groups.scope
            FROM mechanic_condition_groups AS groups
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = groups.mechanic_template_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, groups.group_order
            """,
            (ruleset_id,),
        ).fetchall()
        groups_by_mechanic: dict[
            int, list[MechanicConditionGroupDefinition]
        ] = defaultdict(list)
        for row in group_rows:
            groups_by_mechanic[int(row["mechanic_template_id"])].append(
                MechanicConditionGroupDefinition(
                    order=int(row["group_order"]),
                    operator=str(row["operator"]),
                    join_with_previous=self._optional_text(
                        row["join_with_previous"]
                    ),
                    scope=str(row["scope"]),
                    conditions=tuple(conditions_by_group[int(row["id"])]),
                )
            )
        return conditions_by_group, groups_by_mechanic

    def _steps(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[MechanicStepDefinition]]:
        rows = connection.execute(
            """
            SELECT steps.branch_id, steps.mechanic_template_id,
                   branches.mechanic_template_id AS branch_mechanic_id,
                   steps.step_order, effects.key AS effect_type_key,
                   effects.ruleset_id AS effect_ruleset_id,
                   effects.active AS effect_active,
                   targets.key AS target_type_key,
                   targets.ruleset_id AS target_ruleset_id,
                   targets.active AS target_active,
                   durations.key AS duration_type_key,
                   durations.ruleset_id AS duration_ruleset_id,
                   durations.active AS duration_active,
                   statuses.key AS status_type_key,
                   statuses.ruleset_id AS status_ruleset_id,
                   statuses.active AS status_active, steps.notes
            FROM mechanic_steps AS steps
            JOIN mechanic_branches AS branches ON branches.id = steps.branch_id
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = steps.mechanic_template_id
            JOIN effect_types AS effects ON effects.id = steps.effect_type_id
            JOIN target_types AS targets ON targets.id = steps.target_type_id
            JOIN duration_types AS durations
              ON durations.id = steps.duration_type_id
            LEFT JOIN status_types AS statuses
              ON statuses.id = steps.status_type_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, branches.branch_order,
                     steps.step_order
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicStepDefinition]] = defaultdict(list)
        for row in rows:
            if int(row["mechanic_template_id"]) != int(
                row["branch_mechanic_id"]
            ):
                raise self._invalid(
                    "mechanic step belongs to another mechanic"
                )
            self._validate_lookup(row, "effect", ruleset_id)
            self._validate_lookup(row, "target", ruleset_id)
            self._validate_lookup(row, "duration", ruleset_id)
            self._validate_optional_lookup(row, "status", ruleset_id)
            result[int(row["branch_id"])].append(
                MechanicStepDefinition(
                    order=int(row["step_order"]),
                    effect_type_key=str(row["effect_type_key"]),
                    target_type_key=str(row["target_type_key"]),
                    duration_type_key=str(row["duration_type_key"]),
                    status_type_key=self._optional_text(
                        row["status_type_key"]
                    ),
                    notes=self._optional_text(row["notes"]),
                )
            )
        return result

    def _branch_links(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[MechanicBranchConditionGroupLink]]:
        rows = connection.execute(
            """
            SELECT links.branch_id, links.group_order,
                   links.join_with_previous,
                   groups.group_order AS condition_group_order,
                   branches.mechanic_template_id AS branch_mechanic_id,
                   groups.mechanic_template_id AS group_mechanic_id
            FROM mechanic_branch_condition_groups AS links
            JOIN mechanic_branches AS branches ON branches.id = links.branch_id
            JOIN mechanic_condition_groups AS groups
              ON groups.id = links.condition_group_id
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = branches.mechanic_template_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY,
                     branches.branch_order, links.group_order
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicBranchConditionGroupLink]] = (
            defaultdict(list)
        )
        for row in rows:
            if int(row["branch_mechanic_id"]) != int(row["group_mechanic_id"]):
                raise self._invalid(
                    "branch condition group belongs to another mechanic"
                )
            result[int(row["branch_id"])].append(
                MechanicBranchConditionGroupLink(
                    order=int(row["group_order"]),
                    condition_group_order=int(row["condition_group_order"]),
                    join_with_previous=self._optional_text(
                        row["join_with_previous"]
                    ),
                )
            )
        return result

    def _branches(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
        steps: dict[int, list[MechanicStepDefinition]],
        links: dict[int, list[MechanicBranchConditionGroupLink]],
    ) -> dict[int, list[MechanicBranchDefinition]]:
        rows = connection.execute(
            """
            SELECT branches.id, branches.mechanic_template_id,
                   branches.branch_key, branches.branch_order,
                   branches.branch_type, branches.description,
                   groups.group_order AS direct_group_order,
                   groups.mechanic_template_id AS direct_group_mechanic_id
            FROM mechanic_branches AS branches
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = branches.mechanic_template_id
            LEFT JOIN mechanic_condition_groups AS groups
              ON groups.id = branches.condition_group_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, branches.branch_order
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicBranchDefinition]] = defaultdict(list)
        for row in rows:
            branch_id = int(row["id"])
            branch_links = list(links[branch_id])
            if row["direct_group_order"] is not None:
                if int(row["direct_group_mechanic_id"]) != int(
                    row["mechanic_template_id"]
                ):
                    raise self._invalid(
                        "branch direct condition belongs to another mechanic"
                    )
                direct_order = int(row["direct_group_order"])
                if not any(
                    link.condition_group_order == direct_order
                    for link in branch_links
                ):
                    branch_links.insert(
                        0,
                        MechanicBranchConditionGroupLink(
                            order=1,
                            condition_group_order=direct_order,
                            join_with_previous=None,
                        ),
                    )
            result[int(row["mechanic_template_id"])].append(
                MechanicBranchDefinition(
                    key=str(row["branch_key"]),
                    order=int(row["branch_order"]),
                    branch_type=str(row["branch_type"]),
                    description=self._optional_text(row["description"]),
                    condition_groups=tuple(branch_links),
                    steps=tuple(steps[branch_id]),
                )
            )
        return result

    def _costs(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[MechanicCostDefinition]]:
        rows = connection.execute(
            """
            SELECT costs.mechanic_template_id, costs.cost_order,
                   cost_types.key AS cost_type_key,
                   cost_types.ruleset_id AS cost_ruleset_id,
                   cost_types.active AS cost_active,
                   targets.key AS target_type_key,
                   targets.ruleset_id AS target_ruleset_id,
                   targets.active AS target_active,
                   costs.amount, costs.notes
            FROM mechanic_costs AS costs
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = costs.mechanic_template_id
            JOIN cost_types ON cost_types.id = costs.cost_type_id
            LEFT JOIN target_types AS targets
              ON targets.id = costs.target_type_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, costs.cost_order
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicCostDefinition]] = defaultdict(list)
        for row in rows:
            self._validate_lookup(row, "cost", ruleset_id)
            self._validate_optional_lookup(row, "target", ruleset_id)
            result[int(row["mechanic_template_id"])].append(
                MechanicCostDefinition(
                    order=int(row["cost_order"]),
                    cost_type_key=str(row["cost_type_key"]),
                    target_type_key=self._optional_text(
                        row["target_type_key"]
                    ),
                    amount=self._optional_int(row["amount"]),
                    notes=self._optional_text(row["notes"]),
                )
            )
        return result

    def _parameters(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[MechanicParameterDefinition]]:
        enum_rows = connection.execute(
            """
            SELECT enum_values.parameter_id, enum_values.value_key,
                   enum_values.sort_order, enum_values.description
            FROM mechanic_parameter_enum_values AS enum_values
            JOIN mechanic_parameters AS parameters
              ON parameters.id = enum_values.parameter_id
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = parameters.mechanic_template_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY, parameters.param_key,
                     enum_values.sort_order
            """,
            (ruleset_id,),
        ).fetchall()
        enum_by_parameter: dict[int, list[MechanicParameterEnumValue]] = (
            defaultdict(list)
        )
        for row in enum_rows:
            enum_by_parameter[int(row["parameter_id"])].append(
                MechanicParameterEnumValue(
                    key=str(row["value_key"]),
                    sort_order=int(row["sort_order"]),
                    description=self._optional_text(row["description"]),
                )
            )
        rows = connection.execute(
            """
            SELECT parameters.id, parameters.mechanic_template_id,
                   parameters.param_key, parameters.value_type,
                   parameters.min_int, parameters.max_int,
                   parameters.step_int, parameters.default_int,
                   parameters.allowed_values_json,
                   steps.mechanic_template_id AS step_mechanic_id,
                   steps.step_order, branches.branch_key
            FROM mechanic_parameters AS parameters
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = parameters.mechanic_template_id
            LEFT JOIN mechanic_steps AS steps ON steps.id = parameters.step_id
            LEFT JOIN mechanic_branches AS branches
              ON branches.id = steps.branch_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY,
                     parameters.param_key COLLATE BINARY,
                     branches.branch_key COLLATE BINARY, steps.step_order
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicParameterDefinition]] = defaultdict(
            list
        )
        for row in rows:
            if row["step_mechanic_id"] is not None and int(
                row["step_mechanic_id"]
            ) != int(row["mechanic_template_id"]):
                raise self._invalid(
                    "mechanic parameter step belongs to another mechanic"
                )
            parameter_id = int(row["id"])
            result[int(row["mechanic_template_id"])].append(
                MechanicParameterDefinition(
                    key=str(row["param_key"]),
                    branch_key=self._optional_text(row["branch_key"]),
                    step_order=self._optional_int(row["step_order"]),
                    value_type=str(row["value_type"]),
                    min_int=self._optional_int(row["min_int"]),
                    max_int=self._optional_int(row["max_int"]),
                    step_int=self._optional_int(row["step_int"]),
                    default_int=self._optional_int(row["default_int"]),
                    allowed_values=self._allowed_values(
                        row["allowed_values_json"]
                    ),
                    enum_values=tuple(enum_by_parameter[parameter_id]),
                )
            )
        return result

    def _allowed_values(self, raw: object) -> tuple[str, ...]:
        if raw is None:
            return ()
        try:
            parsed = json.loads(str(raw))
        except json.JSONDecodeError as error:
            raise self._invalid(
                "mechanic parameter allowed_values_json is invalid"
            ) from error
        if not isinstance(parsed, list) or any(
            not isinstance(value, str) or not value for value in parsed
        ):
            raise self._invalid(
                "mechanic parameter allowed_values_json must contain text"
            )
        return tuple(parsed)

    def _validate_lookup(
        self,
        row: sqlite3.Row,
        prefix: str,
        ruleset_id: int,
    ) -> None:
        if int(row[f"{prefix}_ruleset_id"]) != ruleset_id or not bool(
            row[f"{prefix}_active"]
        ):
            raise self._invalid(
                f"mechanic {prefix} lookup crosses a ruleset or is inactive"
            )

    def _validate_optional_lookup(
        self,
        row: sqlite3.Row,
        prefix: str,
        ruleset_id: int,
    ) -> None:
        if row[f"{prefix}_type_key"] is not None:
            self._validate_lookup(row, prefix, ruleset_id)

    @staticmethod
    def _optional_int(value: int | None) -> int | None:
        return None if value is None else int(value)

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return None if value is None else str(value)

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
