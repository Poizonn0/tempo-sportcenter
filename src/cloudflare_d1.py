"""Small synchronous adapter for Cloudflare D1 used by Flask's WSGI handlers."""

from pyodide.ffi import run_sync


def _to_python(value):
    if value is None:
        return None
    converter = getattr(value, "to_py", None)
    if callable(converter):
        return converter()
    return value


def _field(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    try:
        return getattr(value, name)
    except (AttributeError, TypeError):
        return default


class D1Row(dict):
    """Mapping row that also supports SQLite's numeric column indexing."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class D1Cursor:
    def __init__(self, result):
        result = _to_python(result)
        meta = _to_python(_field(result, "meta", {})) or {}
        rows = _to_python(_field(result, "results", [])) or []
        self._rows = [D1Row(_to_python(row) or {}) for row in rows]
        self._position = 0
        self.lastrowid = meta.get("last_row_id")
        self.rowcount = meta.get("changes", 0)

    def fetchone(self):
        if self._position >= len(self._rows):
            return None
        row = self._rows[self._position]
        self._position += 1
        return row

    def fetchall(self):
        rows = self._rows[self._position:]
        self._position = len(self._rows)
        return rows

    def __iter__(self):
        return iter(self.fetchall())


class D1Connection:
    def __init__(self, binding):
        self.binding = binding

    def execute(self, sql, parameters=()):
        statement = self.binding.prepare(sql)
        if parameters:
            statement = statement.bind(*parameters)
        # D1's run() returns both result rows and mutation metadata.
        return D1Cursor(run_sync(statement.run()))

    def commit(self):
        # D1 commits each statement automatically.
        return None

    def close(self):
        return None
