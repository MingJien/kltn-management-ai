"""Render six presentation ERDs from the verified, read-only PostgreSQL schema.

Run from the repository root: ``python tools/generate_erd_clusters.py``.
The checked-in manifest fixes the intended database and the layout only; every
column, key, and relationship in the output comes from PostgreSQL introspection.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "design" / "erd-clusters"
MANIFEST = OUT / "clusters.json"


def require_runtime() -> None:
    """The user's plain `python` may lack the project's development packages."""
    if all(importlib.util.find_spec(name) for name in ("sqlalchemy", "PIL")):
        return
    candidate = ROOT / ".venv" / "Scripts" / "python.exe"
    if candidate.exists() and Path(sys.executable).resolve() != candidate.resolve():
        raise SystemExit(subprocess.run([str(candidate), __file__, *sys.argv[1:]], check=False).returncode)
    raise RuntimeError("Cần môi trường Python của dự án với SQLAlchemy và Pillow (.venv).")


require_runtime()
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from backend.db.metadata import target_metadata  # noqa: E402
from backend.db.validate_schema import load_env  # noqa: E402


CARD_W = 780
COL_GAP = 170
ROW_GAP = 190
MARGIN_X = 130
TOP = 235
BOTTOM = 135
HEADER_H = 78
ROW_H = 35
CARD_FOOTER = 44
COLORS = {
    "background": "#F7F9FC",
    "ink": "#14243A",
    "muted": "#52667E",
    "blue": "#1F527B",
    "blue_light": "#EAF2FA",
    "context": "#EEF1F5",
    "context_ink": "#64748B",
    "edge": "#7696B6",
    "border": "#B8C7D8",
    "white": "#FFFFFF",
}


@dataclass(frozen=True)
class Column:
    name: str
    sql_type: str
    nullable: bool
    pk: bool
    fk: bool
    unique: bool


@dataclass(frozen=True)
class ForeignKey:
    name: str
    child: str
    parent: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    unique_child: bool


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    unique_sets: tuple[tuple[str, ...], ...]
    foreign_keys: tuple[ForeignKey, ...]


@dataclass(frozen=True)
class Schema:
    source: str
    database: str
    postgres_version: str
    alembic_revision: str
    tables: dict[str, Table]


def load_manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema") != "public" or not data.get("database"):
        raise ValueError("clusters.json phải xác định database và schema public.")
    if len(data.get("clusters", [])) != 6:
        raise ValueError("clusters.json phải chứa đúng 6 cụm.")
    slugs = [cluster["slug"] for cluster in data["clusters"]]
    if len(set(slugs)) != 6 or any("/" in slug or "\\" in slug for slug in slugs):
        raise ValueError("Slug của 6 cụm phải riêng và không chứa dấu phân cách đường dẫn.")
    for cluster in data["clusters"]:
        names = [name for row in cluster["rows"] for name in row]
        if not names or len(set(names)) != len(names):
            raise ValueError(f"Cụm {cluster['id']} trống hoặc lặp tên bảng.")
        if not set(cluster["context"]).issubset(names):
            raise ValueError(f"Context của cụm {cluster['id']} không nằm trong rows.")
    return data


def metadata_fk_signature(table) -> set[tuple]:
    return {
        (
            tuple(element.parent.name for element in fk.elements),
            fk.referred_table.name,
            tuple(element.column.name for element in fk.elements),
        )
        for fk in table.foreign_key_constraints
    }


def live_schema(database: str) -> Schema:
    # .env is only consumed to authenticate; the URL/password is never printed.
    load_env()
    if "DATABASE_URL" not in os.environ:
        raise RuntimeError("Thiếu DATABASE_URL trong .env local.")
    url = make_url(os.environ["DATABASE_URL"]).set(database=database)
    engine = create_engine(
        url,
        future=True,
        connect_args={"options": "-c default_transaction_read_only=on -c statement_timeout=30000"},
    )
    with engine.connect() as conn:
        identity = conn.execute(
            text("SELECT current_database(), current_setting('transaction_read_only'), current_setting('server_version')")
        ).one()
        if identity[0] != database or identity[1] != "on":
            raise RuntimeError("Kết nối không đúng database hoặc không ở chế độ read-only.")
        inspector = inspect(conn)
        physical = set(inspector.get_table_names(schema="public"))
        if "alembic_version" not in physical:
            raise RuntimeError("Database không có public.alembic_version; không thể xác minh schema KLTN.")
        revision = conn.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
        business = physical - {"alembic_version"}
        model_names = set(target_metadata.tables)
        if business != model_names:
            raise RuntimeError(
                f"Schema PostgreSQL/SQLAlchemy lệch bảng: chỉ ở DB={sorted(business-model_names)}; "
                f"chỉ ở model={sorted(model_names-business)}. Không sinh ERD từ schema không khớp."
            )
        result: dict[str, Table] = {}
        for name in sorted(business):
            raw_cols = inspector.get_columns(name, schema="public")
            db_names = {column["name"] for column in raw_cols}
            model = target_metadata.tables[name]
            if db_names != set(model.columns.keys()):
                raise RuntimeError(f"Cột bảng {name} lệch SQLAlchemy: DB={sorted(db_names)}; model={sorted(model.columns.keys())}")
            pk = tuple(inspector.get_pk_constraint(name, schema="public")["constrained_columns"] or ())
            if set(pk) != {column.name for column in model.primary_key.columns}:
                raise RuntimeError(f"PK bảng {name} lệch SQLAlchemy.")
            raw_fks = inspector.get_foreign_keys(name, schema="public")
            db_fk_signature = {
                (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
                for fk in raw_fks
            }
            if db_fk_signature != metadata_fk_signature(model):
                raise RuntimeError(f"FK bảng {name} lệch SQLAlchemy; không tự thêm/bỏ cạnh.")
            unique_sets = {tuple(item["column_names"]) for item in inspector.get_unique_constraints(name, schema="public") if item.get("column_names")}
            for index in inspector.get_indexes(name, schema="public"):
                if index.get("unique") and index.get("column_names") and not index.get("dialect_options", {}).get("postgresql_where"):
                    unique_sets.add(tuple(index["column_names"]))
            unique_sets.add(pk)
            model_unique_sets = {
                tuple(column.name for column in constraint.columns)
                for constraint in model.constraints
                if constraint.__class__.__name__ == "UniqueConstraint"
            }
            if not model_unique_sets.issubset(unique_sets):
                raise RuntimeError(f"UNIQUE bảng {name} lệch SQLAlchemy.")
            fk_columns = {col for fk in raw_fks for col in fk["constrained_columns"]}
            unique_columns = {col for group in unique_sets for col in group}
            columns = tuple(
                Column(
                    name=column["name"],
                    sql_type=short_type(str(column["type"])),
                    nullable=bool(column["nullable"]),
                    pk=column["name"] in pk,
                    fk=column["name"] in fk_columns,
                    unique=column["name"] in unique_columns,
                )
                for column in raw_cols
            )
            fks = tuple(
                ForeignKey(
                    name=fk["name"] or "_".join(fk["constrained_columns"]),
                    child=name,
                    parent=fk["referred_table"],
                    child_columns=tuple(fk["constrained_columns"]),
                    parent_columns=tuple(fk["referred_columns"]),
                    unique_child=any(set(group).issubset(fk["constrained_columns"]) for group in unique_sets if group),
                )
                for fk in raw_fks
            )
            result[name] = Table(name, columns, pk, tuple(sorted(unique_sets)), fks)
    engine.dispose()
    return Schema("PostgreSQL public (live, read-only)", database, identity[2], revision, result)


def metadata_schema(database: str) -> Schema:
    """Explicit, visibly labelled fallback only when connecting is impossible."""
    result: dict[str, Table] = {}
    for name, table in target_metadata.tables.items():
        pk = tuple(column.name for column in table.primary_key.columns)
        unique_sets = {pk}
        unique_sets.update(tuple(column.name for column in constraint.columns) for constraint in table.constraints if constraint.__class__.__name__ == "UniqueConstraint")
        unique_sets.update(tuple(column.name for column in index.columns) for index in table.indexes if index.unique)
        raw_fks = tuple(table.foreign_key_constraints)
        fk_columns = {element.parent.name for fk in raw_fks for element in fk.elements}
        unique_columns = {col for group in unique_sets for col in group}
        columns = tuple(
            Column(column.name, short_type(str(column.type)), column.nullable, column.name in pk, column.name in fk_columns, column.name in unique_columns)
            for column in table.columns
        )
        fks = tuple(
            ForeignKey(
                fk.name or "_".join(element.parent.name for element in fk.elements),
                name,
                fk.referred_table.name,
                tuple(element.parent.name for element in fk.elements),
                tuple(element.column.name for element in fk.elements),
                any(set(group).issubset({element.parent.name for element in fk.elements}) for group in unique_sets if group),
            )
            for fk in raw_fks
        )
        result[name] = Table(name, columns, pk, tuple(sorted(unique_sets)), fks)
    return Schema("SQLAlchemy metadata (fallback; PostgreSQL unavailable)", database, "không đọc được", "không xác minh live", result)


def short_type(value: str) -> str:
    value = value.lower().replace("timestamp with time zone", "timestamptz")
    value = value.replace("character varying", "varchar").replace("double precision", "float8")
    value = value.replace("boolean", "bool").replace("integer", "int")
    return value[:22]


def chosen_columns(table: Table, context: bool) -> list[Column]:
    audit = {"created_at", "updated_at", "row_version", "created_by", "updated_by", "deleted_at"}
    mandatory = [
        col for col in table.columns
        if col.pk or col.fk or col.unique or (
            col.name not in audit and any(part in col.name for part in ("code", "version", "state", "status"))
        )
    ]
    extras = [col for col in table.columns if col not in mandatory and col.name not in audit]
    def rank(col: Column) -> tuple[int, int]:
        important = ("title", "name", "decision", "result", "score", "points", "ratio", "gpa", "source", "type", "max_", "effective", "reason", "content", "visibility", "scheduled", "role")
        score = next((len(important) - i for i, part in enumerate(important) if part in col.name), 0)
        return (-score, list(table.columns).index(col))
    selected = set(mandatory + sorted(extras, key=rank)[: 2 if context else 5])
    return [col for col in table.columns if col in selected]


def load_font(size: int, bold: bool = False):
    paths = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


class Raster:
    def __init__(self, width: int, height: int):
        self.image = Image.new("RGB", (width, height), COLORS["background"])
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = {(size, bold): load_font(size, bold) for size in (19, 21, 22, 24, 27, 30, 48) for bold in (False, True)}

    def rect(self, xy, fill, outline=None, radius=0, width=2):
        self.draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

    def line(self, points, fill, width=3):
        self.draw.line(points, fill=fill, width=width, joint="curve")

    def text(self, xy, value, size=22, fill=None, bold=False):
        self.draw.text(xy, value, font=self.fonts[(size, bold)], fill=fill or COLORS["ink"])

    def save(self, path: Path):
        self.image.save(path, format="PNG", optimize=True)


class Vector:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                      f'<rect width="{width}" height="{height}" fill="{COLORS["background"]}"/>']

    def rect(self, xy, fill, outline=None, radius=0, width=2):
        x1, y1, x2, y2 = xy
        stroke = outline or fill
        self.parts.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def line(self, points, fill, width=3):
        coords = " ".join(f"{int(x)},{int(y)}" for x, y in points)
        self.parts.append(f'<polyline points="{coords}" fill="none" stroke="{fill}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')

    def text(self, xy, value, size=22, fill=None, bold=False):
        x, y = xy
        weight = "700" if bold else "400"
        # Pillow uses a top coordinate; SVG uses a baseline.
        self.parts.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill or COLORS["ink"]}">{escape(value)}</text>')

    def save(self, path: Path):
        path.write_text("\n".join([*self.parts, "</svg>"]), encoding="utf-8")


def pill(painter, x: int, y: int, label: str, fill: str = "#FFFFFF") -> None:
    width = 22 + 14 * len(label)
    painter.rect((x, y, x + width, y + 31), fill, COLORS["border"], radius=10, width=1)
    painter.text((x + 11, y + 3), label, 19, COLORS["blue"], True)


def card(painter, box: tuple[int, int, int, int], table: Table, shown: list[Column], context: bool) -> None:
    x, y, width, height = box
    base = COLORS["context"] if context else COLORS["white"]
    painter.rect((x, y, x + width, y + height), base, COLORS["border"], radius=17, width=2)
    painter.rect((x, y, x + width, y + HEADER_H), COLORS["context_ink"] if context else COLORS["blue"], radius=16, width=1)
    # Square off the lower header corners while retaining the card's upper corners.
    painter.rect((x + 1, y + HEADER_H - 18, x + width - 1, y + HEADER_H), COLORS["context_ink"] if context else COLORS["blue"])
    painter.text((x + 22, y + 16), table.name, 30, COLORS["white"], True)
    if context:
        painter.text((x + width - 135, y + 23), "CONTEXT", 19, COLORS["white"], True)
    for index, col in enumerate(shown):
        row_y = y + HEADER_H + 9 + index * ROW_H
        if index % 2 == 1:
            painter.rect((x + 2, row_y - 2, x + width - 2, row_y + ROW_H - 1), "#F1F5FA" if not context else "#E6EAF0")
        painter.text((x + 20, row_y), col.name, 22, COLORS["ink"], col.pk)
        painter.text((x + 505, row_y), col.sql_type, 21, COLORS["muted"])
        flags = "/".join(flag for flag, yes in (("PK", col.pk), ("FK", col.fk), ("UK", col.unique and not col.pk)) if yes)
        if flags:
            painter.text((x + 660, row_y), flags, 19, COLORS["blue"], True)
    hidden = len(table.columns) - len(shown)
    footer = f"{len(table.columns)} cột • {len(table.foreign_keys)} FK" + (f" • ẩn {hidden} cột phụ" if hidden else "")
    painter.text((x + 20, y + height - 37), footer, 19, COLORS["muted"])


def boxes_intersect(a, b) -> bool:
    return a[0] < b[0] + b[2] and a[0] + a[2] > b[0] and a[1] < b[1] + b[3] and a[1] + a[3] > b[1]


def segment_hits_box(a, b, box) -> bool:
    x, y, w, h = box
    if a[0] == b[0]:
        return x < a[0] < x+w and max(min(a[1], b[1]), y) < min(max(a[1], b[1]), y+h)
    if a[1] == b[1]:
        return y < a[1] < y+h and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x+w)
    raise AssertionError("ERD edge must use orthogonal segments")


def edge_paths(positions: dict[str, tuple], fks: list[ForeignKey]) -> list[tuple[ForeignKey, list[tuple[int, int]]]]:
    max_row = max(value[4] for value in positions.values())
    incoming: dict[tuple[str, str], list[str]] = defaultdict(list)
    outgoing: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fk in fks:
        if fk.child == fk.parent:
            continue
        parent_row = positions[fk.parent][4]
        child_row = positions[fk.child][4]
        direction = "bottom" if child_row > parent_row or (child_row == parent_row and parent_row < max_row) else "top"
        side = "left" if positions[fk.child][5] > 0 else "right"
        outgoing[(fk.parent, direction)].append(fk.name)
        incoming[(fk.child, side)].append(fk.name)
    paths = []
    for number, fk in enumerate(fks):
        px, py, pw, ph, pr, pc = positions[fk.parent]
        cx, cy, cw, ch, cr, cc = positions[fk.child]
        if fk.child == fk.parent:
            mid = py + min(ph - 70, max(115, ph // 2))
            points = [(px + pw, mid - 24), (px + pw + 74, mid - 24), (px + pw + 74, mid + 28), (px + pw, mid + 28)]
        else:
            direction = "bottom" if cr > pr or (cr == pr and pr < max_row) else "top"
            side = "left" if cc > 0 else "right"
            out = outgoing[(fk.parent, direction)]
            inc = incoming[(fk.child, side)]
            start_shift = (out.index(fk.name) - (len(out) - 1) / 2) * 24
            end_shift = (inc.index(fk.name) - (len(inc) - 1) / 2) * 20
            sx = int(px + pw / 2 + start_shift)
            sy = py + ph if direction == "bottom" else py
            lane = (number % 5 - 2) * 7
            route_y = sy + (59 + lane if direction == "bottom" else -59 - lane)
            route_x = cx - 58 - (number % 4) * 7 if side == "left" else cx + cw + 58 + (number % 4) * 7
            end_x = cx if side == "left" else cx + cw
            end_y = int(cy + ch / 2 + end_shift)
            points = [(sx, sy), (sx, route_y), (route_x, route_y), (route_x, end_y), (end_x, end_y)]
        paths.append((fk, points))
    # All edge corridors must remain clear of unrelated table cards.
    for fk, points in paths:
        for name, (x, y, w, h, _, _) in positions.items():
            if name in (fk.parent, fk.child):
                continue
            if any(segment_hits_box(a, b, (x, y, w, h)) for a, b in zip(points, points[1:])):
                raise AssertionError(f"FK route {fk.name} overlaps unrelated table {name}")
    return paths


def render_cluster(cluster: dict, schema: Schema, generated_at: str) -> tuple[int, int]:
    names = [name for row in cluster["rows"] for name in row]
    missing = set(names) - set(schema.tables)
    if missing:
        raise RuntimeError(f"Cụm {cluster['id']} thiếu bảng trong schema: {sorted(missing)}")
    context = set(cluster["context"])
    shown = {name: chosen_columns(schema.tables[name], name in context) for name in names}
    card_h = HEADER_H + max(len(cols) for cols in shown.values()) * ROW_H + CARD_FOOTER
    cols = max(len(row) for row in cluster["rows"])
    rows = len(cluster["rows"])
    width = MARGIN_X * 2 + cols * CARD_W + (cols - 1) * COL_GAP
    height = TOP + rows * card_h + (rows - 1) * ROW_GAP + BOTTOM
    if width <= height:
        raise AssertionError(f"Cụm {cluster['id']} không còn bố cục landscape")
    positions: dict[str, tuple[int, int, int, int, int, int]] = {}
    for row_no, row in enumerate(cluster["rows"]):
        for col_no, name in enumerate(row):
            positions[name] = (MARGIN_X + col_no * (CARD_W + COL_GAP), TOP + row_no * (card_h + ROW_GAP), CARD_W, card_h, row_no, col_no)
    rects = [(name, value[:4]) for name, value in positions.items()]
    if any(boxes_intersect(a, b) for i, (_, a) in enumerate(rects) for _, b in rects[i+1:]):
        raise AssertionError(f"Cụm {cluster['id']} có bảng chồng nhau")
    fks = sorted((fk for name in names for fk in schema.tables[name].foreign_keys if fk.parent in positions), key=lambda fk: (fk.parent, fk.child, fk.name))
    if not fks:
        raise AssertionError(f"Cụm {cluster['id']} không có FK nội cụm")
    paths = edge_paths(positions, fks)
    for suffix, painter in (("png", Raster(width, height)), ("svg", Vector(width, height))):
        painter.text((MARGIN_X, 44), f"{cluster['id']}  {cluster['title']}", 48, COLORS["ink"], True)
        painter.text((MARGIN_X, 116), f"{schema.database}  •  PostgreSQL {schema.postgres_version}  •  Alembic {schema.alembic_revision}  •  {len(names)} bảng  •  {len(fks)} FK", 24, COLORS["muted"])
        painter.text((MARGIN_X, 162), "Bảng xanh: nghiệp vụ chính    •    Bảng xám: ngữ cảnh    •    Các đường nối lấy từ khóa ngoại thật", 22, COLORS["muted"])
        for fk, points in paths:
            painter.line(points, COLORS["edge"], 3)
        for name, (x, y, w, h, _, _) in positions.items():
            card(painter, (x, y, w, h), schema.tables[name], shown[name], name in context)
        for fk, points in paths:
            start, end = points[0], points[-1]
            # FK direction: parent end is 1; child end is N, or at most 1 if unique.
            if fk.parent == fk.child:
                pill(painter, start[0] + 7, start[1] - 48, "1")
                pill(painter, end[0] + 7, end[1] + 7, "≤1" if fk.unique_child else "N")
            else:
                px, py, pw, ph, pr, pc = positions[fk.parent]
                cx, cy, cw, ch, cr, cc = positions[fk.child]
                pill(painter, start[0] - 19, start[1] + (10 if cr > pr else -42), "1")
                pill(painter, end[0] + (-61 if cc > 0 else 10), end[1] - 36, "≤1" if fk.unique_child else "N")
        footer = f"Nguồn: {schema.source}  •  {generated_at}  •  1 = bảng cha, N = nhiều bản ghi con; ≤1 = FK duy nhất"
        painter.text((MARGIN_X, height - 62), footer, 21, COLORS["muted"])
        painter.save(OUT / f"{cluster['slug']}.{suffix}")
    return len(names), len(fks)


def write_readme(manifest: dict, schema: Schema, stats: dict, generated_at: str) -> None:
    lines = [
        "# ERD theo cụm nghiệp vụ",
        "",
        f"Nguồn tạo: **{schema.source}**. Database: **`{schema.database}`**, schema **`public`**; PostgreSQL **{schema.postgres_version}**; Alembic **`{schema.alembic_revision}`**. Ngày sinh: **{generated_at}**.",
        "",
        "Sáu ảnh được liên kết bên dưới là ERD hiện hành, sinh tự động từ bảng/cột/PK/FK/UNIQUE đã introspect và đối chiếu với SQLAlchemy metadata. Kết nối PostgreSQL đặt `default_transaction_read_only=on`; script không ghi dữ liệu. Các tệp ảnh không được liên kết trong bảng dưới không thuộc bộ ERD hiện hành.",
        "",
        "## Chạy lại bằng một lệnh",
        "",
        "Tại thư mục gốc `D:\\KLTN` (có `.env` local cho kết nối), chạy:",
        "",
        "```powershell",
        "python tools/generate_erd_clusters.py",
        "```",
        "",
        "Cài môi trường lần đầu: `py -m venv .venv`, rồi `.\\.venv\\Scripts\\python.exe -m pip install -e \".[dev]\"`. Sau đó mỗi lần tái sinh chỉ cần lệnh trên.",
        "",
        "Nếu `python` hệ thống thiếu thư viện, script tự chuyển sang `.venv\\Scripts\\python.exe`. Khi PostgreSQL không kết nối được, lệnh mặc định báo lỗi; chỉ dùng `--metadata-fallback` nếu muốn sinh ảnh từ SQLAlchemy metadata và ghi rõ nguồn thay thế.",
        "",
        "## Sáu ảnh",
        "",
        "| Cụm | Ảnh | Bảng chính | Bảng ngữ cảnh | FK nội cụm |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for cluster in manifest["clusters"]:
        all_names = [name for row in cluster["rows"] for name in row]
        context = set(cluster["context"])
        main = [name for name in all_names if name not in context]
        lines.append(
            f"| {cluster['id']} — {cluster['title']} | "
            f"[PNG]({cluster['slug']}.png) · [SVG]({cluster['slug']}.svg) | "
            f"{', '.join(f'`{name}`' for name in main)} | "
            f"{', '.join(f'`{name}`' for name in all_names if name in context) or '—'} | "
            f"{stats[cluster['id']][1]} |"
        )
    lines += [
        "",
        "Mỗi đường nối biểu diễn một FK thật giữa hai bảng trong cụm. `1/N` chỉ quan hệ một-nhiều; `≤1` đánh dấu phía con có khóa duy nhất. `UK` nghĩa là cột thuộc một ràng buộc hoặc chỉ mục UNIQUE, có thể là khóa ghép. FK ra ngoài cụm vẫn được ghi ở cột nhưng không kéo toàn bộ bảng liên quan vào ảnh.",
        "",
        "ERD cụm là các góc nhìn để trình bày. [ERD đầy đủ](../erd-kltn-management.md), [từ điển dữ liệu](../database-dictionary.md) và [SQL schema-only](../../database/official/kltn-management-schema.sql) là nguồn tra cấu trúc hiện hành. Ảnh chỉ hiển thị PK, FK, UNIQUE, trạng thái và một số cột nghiệp vụ để dễ đọc.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def verify_outputs(manifest: dict) -> None:
    expected = {f"{cluster['slug']}.png" for cluster in manifest["clusters"]}
    found = {p.name for p in OUT.glob("*.png")}
    if not expected <= found:
        raise AssertionError(f"Thiếu PNG hiện hành: {sorted(expected-found)}")
    for cluster in manifest["clusters"]:
        png = OUT / f"{cluster['slug']}.png"
        svg = OUT / f"{cluster['slug']}.svg"
        with Image.open(png) as img:
            img.verify()
        with Image.open(png) as img:
            if img.width <= img.height or png.stat().st_size <= 1000:
                raise AssertionError(f"PNG rỗng/không landscape: {png.name}")
            colors = img.resize((256, 160)).convert("RGB").getcolors(maxcolors=256*160)
            if not colors or len(colors) < 8:
                raise AssertionError(f"PNG có vẻ trắng: {png.name}")
        ET.parse(svg)
        if svg.stat().st_size <= 1000:
            raise AssertionError(f"SVG rỗng: {svg.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-fallback", action="store_true", help="Chỉ khi không kết nối PostgreSQL; README ghi rõ nguồn SQLAlchemy metadata")
    args = parser.parse_args()
    manifest = load_manifest()
    try:
        schema = live_schema(manifest["database"])
    except OperationalError as exc:
        if not args.metadata_fallback:
            raise RuntimeError("Không kết nối PostgreSQL canonical; chưa sinh ERD. Có thể dùng --metadata-fallback và ghi rõ nguồn.") from exc
        schema = metadata_schema(manifest["database"])
    configured = {name for cluster in manifest["clusters"] for row in cluster["rows"] for name in row}
    if configured != set(schema.tables):
        raise RuntimeError(f"Bộ cụm không bao phủ đúng schema: thiếu={sorted(set(schema.tables)-configured)}, thừa={sorted(configured-set(schema.tables))}")
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    stats = {}
    for cluster in manifest["clusters"]:
        stats[cluster["id"]] = render_cluster(cluster, schema, generated_at)
    write_readme(manifest, schema, stats, generated_at)
    verify_outputs(manifest)
    print(f"PASS: {schema.source}; database={schema.database}; PostgreSQL={schema.postgres_version}; Alembic={schema.alembic_revision}")
    for cluster in manifest["clusters"]:
        tables, fks = stats[cluster["id"]]
        print(f"  {cluster['slug']}: {tables} bảng, {fks} FK, PNG+SVG")
    print("Không ghi PostgreSQL; 6 PNG/SVG đã kiểm mở, landscape và có nội dung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
