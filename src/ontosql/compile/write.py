"""Compile semantic instances to INSERT/UPDATE/DELETE plans (public re-exports)."""

from ontosql.compile.columns import column_key, count_scalar
from ontosql.compile.errors import WriteCompileError
from ontosql.compile.save_plan import compile_delete_plan, compile_save_plan

# Backward-compatible aliases
_column_key = column_key

__all__ = [
    "WriteCompileError",
    "_column_key",
    "column_key",
    "compile_delete_plan",
    "compile_save_plan",
    "count_scalar",
]
