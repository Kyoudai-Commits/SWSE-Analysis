"""Minimal, dependency-free .xlsx / .xlsm reader (stdlib only).

Why not openpyxl: the build must be reproducible in any clean sandbox with no
network/pip access. Everything we need from a spreadsheet is: sheet names, the
sheet order, and the *cached* cell values (formula results as last saved by
Excel/LibreOffice). That is a small amount of XML.

Supported: shared strings, inline strings, cached formula values, numbers,
boolean, error values, merged-cell layout (ignored), hyperlinks in
``Links``-style columns (ignored). Skipped on purpose: styles, VBA, drawings,
charts, data validation, conditional formatting.
"""

from __future__ import annotations

import datetime as _dt
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

_NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

_CELL_REF = re.compile(r"^([A-Z]{1,3})([0-9]+)$")

# Excel 1900 serial epoch (with the historic leap-year bug).
_EXCEL_EPOCH = _dt.datetime(1899, 12, 30)
# Styles whose numFmtId marks a date/time (built-in formats).
_DATE_BUILTIN_FMTS = set(range(14, 23)) | set(range(45, 48)) | {27, 30, 36, 50, 57}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _col_to_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _decode(value: str, cell_type: str):
    if cell_type in ("s", "str", "e"):
        return value
    if cell_type == "b":
        return value == "1"
    if cell_type == "inlineStr":
        return value
    # numeric or date
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    return f


class Sheet:
    """A single worksheet: an ordered list of rows of (col_index -> value)."""

    def __init__(self, name: str, index: int, path: str, dim: str | None):
        self.name = name
        self.index = index
        self.path = path
        self.dim = dim
        self._rows: dict[int, dict[int, object]] = {}
        self.max_row = 0
        self.max_col = 0

    def _add(self, r: int, c: int, value) -> None:
        if value is None or value == "":
            return
        row = self._rows.setdefault(r, {})
        row[c] = value
        if r > self.max_row:
            self.max_row = r
        if c > self.max_col:
            self.max_col = c

    @property
    def n_rows(self) -> int:
        return self.max_row

    def grid(self) -> list[list]:
        """Dense row-major grid with ``None`` for empty cells."""
        out = []
        for r in range(1, self.max_row + 1):
            row = self._rows.get(r)
            if not row:
                out.append([None] * (self.max_col + 1))
                continue
            out.append([row.get(c) for c in range(self.max_col + 1)])
        return out

    def cells(self):
        """Yield (row_index, col_index, value) for every non-empty cell."""
        for r in sorted(self._rows):
            for c in sorted(self._rows[r]):
                v = self._rows[r][c]
                if v is not None and v != "":
                    yield r, c, v

    def filled_rows(self) -> list[list]:
        """Rows containing at least one non-empty cell."""
        return [row for row in self.grid() if any(v not in (None, "") for v in row)]


class Workbook:
    def __init__(self, path: str):
        self.path = path
        self._zf = zipfile.ZipFile(path)
        self.shared: list[str] = self._read_shared()
        self.date_style_ids: set[int] = self._read_date_styles()
        self.sheets: list[Sheet] = self._read_sheets()
        self.by_name: dict[str, Sheet] = {s.name: s for s in self.sheets}

    # -- package plumbing -------------------------------------------------
    def _xml(self, name: str):
        try:
            data = self._zf.read(name)
        except KeyError:
            return None
        return ET.fromstring(data)

    def _read_shared(self) -> list[str]:
        root = self._xml("xl/sharedStrings.xml")
        out: list[str] = []
        if root is None:
            return out
        for si in root:
            if _local(si.tag) != "si":
                continue
            parts = []
            for node in si.iter():
                if _local(node.tag) == "t" and node.text:
                    parts.append(node.text)
            out.append("".join(parts))
        return out

    def _read_date_styles(self) -> set[int]:
        """Return the cellXfs indices that render a numeric serial as a date."""
        root = self._xml("xl/styles.xml")
        if root is None:
            return set()
        custom_date: set[int] = set()
        custom = root.find(f"{_NS_MAIN}numFmts")
        if custom is not None:
            for nf in custom:
                code = (nf.get("formatCode") or "").lower()
                if re.search(r"[dmyhs]", code) and "general" not in code and "@" not in code:
                    try:
                        custom_date.add(int(nf.get("numFmtId")))
                    except (TypeError, ValueError):
                        pass
        out: set[int] = set()
        cxfs = root.find(f"{_NS_MAIN}cellXfs")
        if cxfs is not None:
            for i, xf in enumerate(cxfs):
                try:
                    fmt = int(xf.get("numFmtId", "0"))
                except (TypeError, ValueError):
                    continue
                if fmt in _DATE_BUILTIN_FMTS or fmt in custom_date:
                    out.add(i)
        return out

    def _read_sheets(self) -> list[Sheet]:
        rels = {}
        root = self._xml("xl/_rels/workbook.xml.rels")
        if root is not None:
            for rel in root:
                rels[rel.get("Id")] = rel.get("Target")
        wb = self._xml("xl/workbook.xml")
        sheets: list[Sheet] = []
        if wb is None:
            return sheets
        book_views = wb.find(f"{_NS_MAIN}sheets")
        for i, sh in enumerate(book_views or []):
            rid = sh.get(f"{_NS_REL}id")
            target = rels.get(rid) or ""
            if target.startswith("/"):
                path = target.lstrip("/")
            else:
                path = posixpath.normpath(posixpath.join("xl", target))
            sheets.append(Sheet(sh.get("name") or f"Sheet{i+1}", i, path, None))
        # second pass: read each sheet body
        for s in sheets:
            self._read_sheet(s)
        return sheets

    def _read_sheet(self, sheet: Sheet) -> None:
        root = self._xml(sheet.path)
        if root is None:
            return
        dim = root.find(f"{_NS_MAIN}dimension")
        if dim is not None:
            sheet.dim = dim.get("ref")
        data = root.find(f"{_NS_MAIN}sheetData")
        if data is None:
            return
        for row in data:
            if _local(row.tag) != "row":
                continue
            try:
                rnum = int(row.get("r", "0"))
            except ValueError:
                continue
            if rnum == 0:
                continue
            auto = 0
            for cell in row:
                if _local(cell.tag) != "c":
                    continue
                ref = cell.get("r") or ""
                m = _CELL_REF.match(ref)
                if m:
                    cnum = _col_to_index(m.group(1))
                else:
                    cnum = auto
                auto = cnum + 1
                ctype = cell.get("t", "n")
                value = None
                if ctype == "inlineStr":
                    parts = [n.text for n in cell.iter() if _local(n.tag) == "t" and n.text]
                    value = "".join(parts)
                else:
                    vnode = None
                    for child in cell:
                        if _local(child.tag) == "v":
                            vnode = child
                            break
                    if vnode is not None and vnode.text is not None:
                        raw = vnode.text
                        if ctype == "s":
                            try:
                                value = self.shared[int(raw)]
                            except (ValueError, IndexError):
                                value = raw
                        elif ctype == "d":
                            value = raw
                        else:
                            value = _decode(raw, ctype)
                            if (
                                isinstance(value, float)
                                and cell.get("s") is not None
                                and int(cell.get("s")) in self.date_style_ids
                            ):
                                value = _excel_serial_to_dt(value)
                if value is not None:
                    sheet._add(rnum, cnum, value)

    def sheet(self, name: str) -> Sheet:
        return self.by_name[name]


def _excel_serial_to_dt(serial: float):
    try:
        return (_EXCEL_EPOCH + _dt.timedelta(days=serial)).strftime("%Y-%m-%d")
    except (OverflowError, ValueError):
        return serial


def read(path: str) -> Workbook:
    return Workbook(path)
