import datetime
from zoneinfo import ZoneInfo

import structlog

from posthog.schema import (
    CachedErrorTrackingBreakdownsQueryResponse,
    ErrorTrackingBreakdownsQuery,
    ErrorTrackingBreakdownsQueryResponse,
)

from posthog.hogql import ast
from posthog.hogql.query import execute_hogql_query

from posthog.hogql_queries.query_runner import AnalyticsQueryRunner
from posthog.utils import relative_date_parse

logger = structlog.get_logger(__name__)

POSTHOG_BREAKDOWN_NULL_VALUE = "$$_posthog_breakdown_null_$$"


class ErrorTrackingBreakdownsQueryRunner(AnalyticsQueryRunner[ErrorTrackingBreakdownsQueryResponse]):
    query: ErrorTrackingBreakdownsQuery
    cached_response: CachedErrorTrackingBreakdownsQueryResponse

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_from = self.parse_relative_date_from(self.query.dateRange.date_from if self.query.dateRange else None)
        self.date_to = self.parse_relative_date_to(self.query.dateRange.date_to if self.query.dateRange else None)

    @classmethod
    def parse_relative_date_from(cls, date: str | None) -> datetime.datetime:
        if date == "all" or date is None:
            return datetime.datetime.now(tz=ZoneInfo("UTC")) - datetime.timedelta(days=7)

        return relative_date_parse(date, now=datetime.datetime.now(tz=ZoneInfo("UTC")), timezone_info=ZoneInfo("UTC"))

    @classmethod
    def parse_relative_date_to(cls, date: str | None) -> datetime.datetime:
        if not date:
            return datetime.datetime.now(tz=ZoneInfo("UTC"))
        if date == "all":
            raise ValueError("Invalid date range")

        return relative_date_parse(date, ZoneInfo("UTC"), increase=True)

    def to_query(self) -> ast.SelectQuery:
        # Build arrayJoin tuples for each breakdown property
        # Each tuple is (property_name, property_value)
        array_elements: list[ast.Expr] = []
        for prop in self.query.breakdownProperties:
            tuple_elements = [
                ast.Constant(value=prop),
                ast.Call(
                    name="ifNull",
                    args=[
                        ast.Call(name="toString", args=[ast.Field(chain=["properties", prop])]),
                        ast.Constant(value=POSTHOG_BREAKDOWN_NULL_VALUE),
                    ],
                ),
            ]
            array_elements.append(ast.Tuple(exprs=tuple_elements))

        # Innermost subquery: select breakdown tuples from events
        innermost_select = ast.SelectQuery(
            select=[
                ast.Alias(
                    alias="breakdown_tuple",
                    expr=ast.Call(name="arrayJoin", args=[ast.Array(exprs=array_elements)]),
                )
            ],
            select_from=ast.JoinExpr(table=ast.Field(chain=["events"])),
            where=self._build_where_clause(),
        )

        # Second level: extract tuple elements
        second_select = ast.SelectQuery(
            select=[
                ast.Alias(
                    alias="breakdown_property",
                    expr=ast.Call(
                        name="tupleElement", args=[ast.Field(chain=["breakdown_tuple"]), ast.Constant(value=1)]
                    ),
                ),
                ast.Alias(
                    alias="breakdown_value",
                    expr=ast.Call(
                        name="tupleElement", args=[ast.Field(chain=["breakdown_tuple"]), ast.Constant(value=2)]
                    ),
                ),
            ],
            select_from=ast.JoinExpr(table=innermost_select),
        )

        # Third level: group by and count
        third_select = ast.SelectQuery(
            select=[
                ast.Field(chain=["breakdown_property"]),
                ast.Field(chain=["breakdown_value"]),
                ast.Alias(alias="count", expr=ast.Call(name="count", args=[])),
                ast.Alias(
                    alias="total_count",
                    expr=ast.WindowFunction(
                        name="sum",
                        args=[ast.Field(chain=["count"])],
                        over_expr=ast.WindowExpr(
                            partition_by=[ast.Field(chain=["breakdown_property"])],
                        ),
                    ),
                ),
            ],
            select_from=ast.JoinExpr(table=second_select),
            group_by=[ast.Field(chain=["breakdown_property"]), ast.Field(chain=["breakdown_value"])],
        )

        # Fourth level: add row_number window function
        fourth_select = ast.SelectQuery(
            select=[
                ast.Field(chain=["breakdown_property"]),
                ast.Field(chain=["breakdown_value"]),
                ast.Field(chain=["count"]),
                ast.Field(chain=["total_count"]),
                ast.Alias(
                    alias="rn",
                    expr=ast.WindowFunction(
                        name="row_number",
                        args=[],
                        over_expr=ast.WindowExpr(
                            partition_by=[ast.Field(chain=["breakdown_property"])],
                            order_by=[ast.OrderExpr(expr=ast.Field(chain=["count"]), order="DESC")],
                        ),
                    ),
                ),
            ],
            select_from=ast.JoinExpr(table=third_select),
        )

        # Final select: filter by row number limit
        limit_value = self.query.limit if self.query.limit is not None else 3
        final_select = ast.SelectQuery(
            select=[
                ast.Field(chain=["breakdown_property"]),
                ast.Field(chain=["breakdown_value"]),
                ast.Field(chain=["count"]),
                ast.Field(chain=["total_count"]),
            ],
            select_from=ast.JoinExpr(table=fourth_select),
            where=ast.CompareOperation(
                left=ast.Field(chain=["rn"]), right=ast.Constant(value=limit_value), op=ast.CompareOperationOp.LtEq
            ),
            order_by=[
                ast.OrderExpr(expr=ast.Field(chain=["breakdown_property"]), order="ASC"),
                ast.OrderExpr(expr=ast.Field(chain=["count"]), order="DESC"),
            ],
        )

        return final_select

    def _build_where_clause(self) -> ast.Expr:
        conditions: list[ast.Expr] = []

        # Filter by timestamp
        conditions.append(
            ast.CompareOperation(
                left=ast.Field(chain=["timestamp"]),
                right=ast.Constant(value=self.date_from),
                op=ast.CompareOperationOp.GtEq,
            )
        )
        conditions.append(
            ast.CompareOperation(
                left=ast.Field(chain=["timestamp"]),
                right=ast.Constant(value=self.date_to),
                op=ast.CompareOperationOp.LtEq,
            )
        )

        # Filter by event type
        conditions.append(
            ast.CompareOperation(
                left=ast.Field(chain=["event"]), right=ast.Constant(value="$exception"), op=ast.CompareOperationOp.Eq
            )
        )

        # Filter by issue ID
        conditions.append(
            ast.CompareOperation(
                left=ast.Field(chain=["properties", "$exception_issue_id"]),
                right=ast.Constant(value=self.query.issueId),
                op=ast.CompareOperationOp.Eq,
            )
        )

        # Filter test accounts if needed
        if self.query.filterTestAccounts:
            conditions.append(
                ast.CompareOperation(
                    left=ast.Call(
                        name="ifNull",
                        args=[
                            ast.Field(chain=["properties", "$is_identified"]),
                            ast.Constant(value=False),
                        ],
                    ),
                    right=ast.Constant(value=True),
                    op=ast.CompareOperationOp.Eq,
                )
            )

        return ast.And(exprs=conditions)

    def _calculate(self):
        with self.timings.measure("error_tracking_breakdowns_hogql_execute"):
            query_result = execute_hogql_query(
                query=self.to_query(),
                team=self.team,
                query_type="ErrorTrackingBreakdownsQuery",
                timings=self.timings,
                modifiers=self.modifiers,
                limit_context=self.limit_context,
            )

        # Group results by breakdown_property
        grouped_results: dict[str, dict] = {}
        for row in query_result.results:
            breakdown_property = str(row[0])
            breakdown_value = str(row[1])
            count = int(row[2])
            total_count = int(row[3])

            if breakdown_property not in grouped_results:
                grouped_results[breakdown_property] = {"values": [], "total_count": total_count}

            grouped_results[breakdown_property]["values"].append({"breakdown_value": breakdown_value, "count": count})

        return ErrorTrackingBreakdownsQueryResponse(
            results=grouped_results,
            timings=query_result.timings,
            hogql=query_result.hogql,
            modifiers=self.modifiers,
        )
