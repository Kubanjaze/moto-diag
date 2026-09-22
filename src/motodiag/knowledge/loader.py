"""Knowledge base loader — import DTC codes and other data from JSON files."""

import json
from datetime import datetime
from pathlib import Path

from motodiag.core.models import DTCCategory, DTCCode, SymptomCategory, Severity
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.knowledge.symptom_repo import add_symptom
from motodiag.knowledge.issues_repo import add_known_issue


def backfill_row_applicability(conn) -> int:
    """Declare applicability on already-seeded rows. Returns rows changed.

    Phase 255's `post_apply` hook for migration 063. The twelve Phase 254
    CVT rows are already in the operator's database, written before there
    was any column to declare them in, and a fix in the loader only reaches
    a database someone re-seeds. This updates one column on the rows that
    are already there.

    Matched on `(title, make)` and applied with an UPDATE, so
    `known_issues.id` never changes -- the same discipline migration 062
    used, and for the same reason.

    Every seed file is read, not just 254's: a file that declares nothing
    contributes nothing, which is every file written before this phase.
    Rows the seed files do not mention are left alone, because an operator
    may have loaded their own and this migration has no opinion about it.
    """
    from motodiag.knowledge.applicability import dump_applicability

    seed_dir = Path(__file__).parent / "seed" / "knowledge"
    changed = 0
    for path in sorted(seed_dir.glob("*.json")):
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or "applicability" not in item:
                continue
            payload = dump_applicability(item["applicability"])
            if payload is None:
                continue
            cur = conn.execute(
                "UPDATE known_issues SET applicability = ? "
                " WHERE title = ? AND make IS ?",
                (payload, item.get("title"), item.get("make")),
            )
            changed += cur.rowcount or 0
    return changed


#: Phase 255B. Row edits applied by IDENTITY rather than by re-seeding.
#:
#: `known_issues` has a UNIQUE index on
#: `(COALESCE(make,''), COALESCE(model,''), title)` and `add_known_issue`
#: upserts with `ON CONFLICT DO NOTHING`. So a seed edit that touches any of
#: those three columns does NOT update the existing row on a re-seed -- the
#: conflict never fires and a SECOND row is inserted. Demonstrated while
#: planning 255B: re-seeding `known_issues_cvt.json` after dropping the Filly
#: from 4609's model column took the corpus from 12 rows to 13, leaving the
#: over-claiming row in place alongside its replacement. Filed as F129.
#:
#: Every edit below therefore matches the row's OLD identity and issues an
#: UPDATE, so `known_issues.id` never changes -- the discipline migrations
#: 062 and 063 used, and for the same reason.
_255B_MODEL_EDITS: tuple[tuple[str, str, str, str], ...] = (
    (
        "A Kymco service manual gives four CVT figures twice",
        "Kymco",
        "Agility 50, Agility 125, People S 250, People 250, Filly LX 50",
        "Agility 50, Agility 125, People S 250, People 250",
    ),
    (
        # 4615's CVT half. `SYM Symba` leaves, because the lookup classifies
        # the Symba `semi_auto_centrifugal` from SYM's own manual and this
        # half declares {cvt}. `Vespa 946` deliberately STAYS: it is a live
        # KNOWN_SELF_EXCLUDING entry the operator ruled stays as-is (F119,
        # closed-unobtainable), and moving it would silently resolve a pin
        # this phase was not asked to touch.
        "What the regulator record shows for scooter CVTs",
        "Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine",
        "XC155, Vespa GTS, Vespa Primavera, Vespa 946, Piaggio MP3, "
        "Honda Metropolitan, Kymco Agility, Kymco Like 150i, SYM Symba, "
        "Genuine Buddy, Genuine Buddy Kick",
        "XC155, Vespa GTS, Vespa Primavera, Vespa 946, Piaggio MP3, "
        "Honda Metropolitan, Kymco Agility, Kymco Like 150i, "
        "Genuine Buddy, Genuine Buddy Kick",
    ),
)

#: F115. Row 4605 is a vocabulary row: three mechanically unrelated
#: components are all called a drive belt. Its make column reached the
#: scooter marques and not the marques whose owners produce the collision,
#: so the owners it exists to inform could not receive it.
#:
#: The list is measured, not chosen. Vocabulary `drive belt` over
#: title||description||symptoms across all 1,045 rows returns 13 (positive
#: control: 4605 is in its own set). Five carry a non-CVT meaning --
#: 188 Harley-Davidson final drive, 1312 Harley-Davidson/LiveWire final
#: drive, 715 and 870 BMW alternator, 579 Yamaha final drive. Yamaha was
#: already in the column, so three marques are added.
#:
#: MAKES ONLY, not models: `make_wide` is the tier that carries this, and
#: naming a model no document establishes is the 4609 mistake repaired one
#: commit away.
_255B_MAKE_EDITS: tuple[tuple[str, str, str], ...] = (
    (
        "Three unrelated components are all called a drive belt",
        "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine",
        "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine, "
        "Harley-Davidson, BMW, LiveWire",
    ),
)

#: Rows 255B ADDS, by title. The prose lives in the seed file and nowhere
#: else -- this hook reads it from there rather than carrying a second copy
#: that could drift from the one the loader uses.
_255B_NEW_ROW_TITLES: tuple[str, ...] = (
    "The regulator's two indexes contradict each other, and an empty recall "
    "answer is not a clean record",
    "A kickstart that works when the starter button does not is a "
    "brake-lever switch test",
)

#: The seed file 255B's new rows live in.
_255B_SEED = "known_issues_cvt.json"


def _insert_255B_new_rows(conn) -> int:
    """Insert 255B's added rows if they are not already present.

    Reads them from the seed file so the prose has exactly one home. Keyed
    on the full title, which is what the identity index uses; a row already
    present is skipped rather than duplicated, so the hook is idempotent.
    """
    from motodiag.knowledge.applicability import dump_applicability

    path = Path(__file__).parent / "seed" / "knowledge" / _255B_SEED
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    by_title = {i.get("title"): i for i in items if isinstance(i, dict)}

    inserted = 0
    for title in _255B_NEW_ROW_TITLES:
        item = by_title.get(title)
        if item is None:
            raise ValueError(
                f"migration 065 expects {title!r} in {_255B_SEED} and it is not "
                "there -- the seed file and the migration have drifted"
            )
        present = conn.execute(
            "SELECT 1 FROM known_issues WHERE title = ? AND make IS ? AND model IS ?",
            (title, item.get("make"), item.get("model")),
        ).fetchone()
        if present:
            continue
        conn.execute(
            """INSERT INTO known_issues
               (title, description, make, model, year_start, year_end, severity,
                symptoms, dtc_codes, causes, fix_procedure, parts_needed,
                estimated_hours, source, applicability, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["title"], item["description"], item.get("make"),
                item.get("model"), item.get("year_start"), item.get("year_end"),
                item.get("severity", "medium"),
                json.dumps(item.get("symptoms") or []),
                json.dumps(item.get("dtc_codes") or []),
                json.dumps(item.get("causes") or []),
                item.get("fix_procedure"),
                json.dumps(item.get("parts_needed") or []),
                item.get("estimated_hours"),
                item.get("source", "unverified"),
                dump_applicability(item.get("applicability")),
                datetime.now().isoformat(),
            ),
        )
        inserted += 1
    return inserted


def reconcile_255B_rows(conn) -> int:
    """Phase 255B's row edits, applied to an already-seeded database.

    Returns the number of `known_issues` rows changed.

    `post_apply` hook for migration 065. The operator's database already
    holds these rows, and a seed-file edit only reaches a database someone
    re-seeds -- which, for an identity-column edit, would duplicate rather
    than update (see `_255B_MODEL_EDITS`).

    Both junctions are rebuilt at the end because `known_issue_makes` and
    `known_issue_models` are derived from the `make` and `model` columns,
    and this hook edits both. Rebuilding is authoritative rather than
    incremental for the reason Phase 244F gives: the vocabulary is a
    function of the whole corpus.

    Idempotent. An edit whose old value is already gone matches nothing and
    contributes nothing, so a re-run is a no-op rather than an error.
    """
    from motodiag.knowledge.marques import rebuild_make_index
    from motodiag.knowledge.models import rebuild_model_index

    changed = 0
    for title_prefix, make, old_model, new_model in _255B_MODEL_EDITS:
        cur = conn.execute(
            "UPDATE known_issues SET model = ? "
            " WHERE title LIKE ? AND make IS ? AND model IS ?",
            (new_model, title_prefix + "%", make, old_model),
        )
        changed += cur.rowcount or 0

    for title_prefix, old_make, new_make in _255B_MAKE_EDITS:
        cur = conn.execute(
            "UPDATE known_issues SET make = ? "
            " WHERE title LIKE ? AND make IS ?",
            (new_make, title_prefix + "%", old_make),
        )
        changed += cur.rowcount or 0

    changed += _insert_255B_new_rows(conn)

    rebuild_make_index(conn)
    rebuild_model_index(conn)
    return changed


def backfill_dtc_categories(conn) -> int:
    """Classify already-seeded DTC rows from the seed files. Returns rows changed.

    Phase 244R's `post_apply` hook for migration 062. The operator's database
    holds 99 rows written before the loader read `dtc_category`, all of them
    `unknown`. Re-seeding would fix them, but `add_dtc` is INSERT OR REPLACE
    without an id, so a re-seed churns `dtc_codes.id`; this updates one column
    and leaves the rows where they are.

    Matched on `(code, make)`, the pair the loader itself dedupes on. Rows the
    seed files do not mention are left alone: an operator may have loaded
    their own file, and this migration has no opinion about it.

    Idempotent — running it twice changes nothing the second time, which
    matters because Phase 244H recorded a regression run applying migrations
    to the operator's real database twice in one day.
    """
    import json as _json

    from motodiag.core.config import SEED_DATA_DIR

    seed_dir = Path(SEED_DATA_DIR) / "dtc_codes"
    if not seed_dir.is_dir():
        return 0

    changed = 0
    for path in sorted(seed_dir.glob("*.json")):
        try:
            entries = _json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in entries:
            category = item.get("dtc_category")
            if not category:
                continue
            code = str(item["code"]).upper()
            make = item.get("make")
            if make is None:
                cursor = conn.execute(
                    "UPDATE dtc_codes SET dtc_category = ? "
                    "WHERE code = ? AND make IS NULL AND dtc_category IS NOT ?",
                    (category, code, category),
                )
            else:
                cursor = conn.execute(
                    "UPDATE dtc_codes SET dtc_category = ? "
                    "WHERE code = ? AND make = ? AND dtc_category IS NOT ?",
                    (category, code, make, category),
                )
            changed += cursor.rowcount if cursor.rowcount > 0 else 0
    return changed


def _dtc_from_seed(item: dict) -> DTCCode:
    """Build one DTCCode from a seed entry.

    Phase 244R. `dtc_category` used to be absent here, so every row this
    loader ever wrote took the field default — `DTCCategory.UNKNOWN` — and
    `dtc_repo.add_dtc` persisted it faithfully. This loader is the only
    production writer of `dtc_codes`, so that one omission put all 99 seeded
    codes in `unknown` and left `motodiag code --category engine` answering
    "No DTCs found" over 29 engine codes.

    Read tolerantly, like every other field here: a seed file without the key
    still loads, and the corpus guard in
    tests/test_phase244R_dtc_taxonomy.py is what holds the shipped files to
    having one.
    """
    return DTCCode(
        code=item["code"],
        description=item["description"],
        category=SymptomCategory(item.get("category", "other")),
        dtc_category=DTCCategory(item.get("dtc_category", "unknown")),
        severity=Severity(item.get("severity", "medium")),
        make=item.get("make"),
        common_causes=item.get("common_causes", []),
        fix_summary=item.get("fix_summary"),
    )


def load_dtc_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load DTCs from a JSON file into the database.

    JSON format: array of objects with keys matching DTCCode fields.
    Returns number of DTCs loaded.

    Phase 190 commit 8 (Bug 3a fix). Pre-deletes existing rows
    matching the (code, make) pairs in the file before inserting,
    so re-seeding the same file is idempotent. Necessary because
    SQLite's UNIQUE(code, make) constraint on `dtc_codes` does NOT
    catch duplicates when `make IS NULL` (NULL is not equal to NULL
    in UNIQUE semantics) — without this pre-delete, every
    `motodiag db init` (or any caller of this loader) would insert
    another copy of every generic row, accumulating duplicates and
    breaking direct-lookup determinism. Existing dev DBs that
    accumulated duplicates pre-fix self-clean on the next
    re-seed via this pre-delete.
    """
    from motodiag.core.database import get_connection

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DTC file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    # Phase 244R: build and validate every row BEFORE deleting anything.
    #
    # The pre-delete below commits in its own transaction, and the inserts
    # run afterwards. Reading `dtc_category` adds a value that can raise on a
    # typo, which would abort the insert pass with this file's codes already
    # deleted — a seed file with one bad category would silently empty a
    # make. Parsing first means a bad file changes nothing at all.
    parsed = [_dtc_from_seed(item) for item in data]

    # Pre-delete any rows that match (code, make) pairs about to be
    # inserted. This is the dedupe step — UNIQUE(code, make) doesn't
    # enforce uniqueness for NULL-make rows, so we have to clean
    # them ourselves before INSERT OR REPLACE runs. Done in one
    # transaction so a partial seed leaves the DB at the prior
    # committed state.
    with get_connection(db_path) as conn:
        for item in data:
            code = str(item["code"]).upper()
            make = item.get("make")
            if make is None:
                conn.execute(
                    "DELETE FROM dtc_codes WHERE code = ? AND make IS NULL",
                    (code,),
                )
            else:
                conn.execute(
                    "DELETE FROM dtc_codes WHERE code = ? AND make = ?",
                    (code, make),
                )

    count = 0
    for dtc in parsed:
        add_dtc(dtc, db_path)
        count += 1

    return count


def load_dtc_directory(dir_path: str | Path, db_path: str | None = None) -> dict[str, int]:
    """Load all .json DTC files from a directory.

    Returns dict of {filename: count_loaded}.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    results = {}
    for json_file in sorted(path.glob("*.json")):
        count = load_dtc_file(json_file, db_path)
        results[json_file.name] = count

    return results


def load_symptom_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load symptoms from a JSON file into the database.

    JSON format: array of objects with name, description, category, related_systems.
    Returns number of symptoms loaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Symptom file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    count = 0
    for item in data:
        add_symptom(
            name=item["name"],
            description=item["description"],
            category=item.get("category", "other"),
            related_systems=item.get("related_systems", []),
            db_path=db_path,
        )
        count += 1

    return count


def load_known_issues_file(file_path: str | Path, db_path: str | None = None) -> int:
    """Load known issues from a JSON file into the database.

    JSON format: array of objects matching add_known_issue() parameters.
    Returns number of issues loaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Known issues file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    # Phase 244D: report rows actually inserted, not items walked. The old
    # counter incremented per item regardless of outcome, so once loading
    # became idempotent a repeat load still claimed to have inserted every
    # entry. On a fresh database the two are identical; on a re-seed the
    # difference is the whole point.
    from motodiag.knowledge.issues_repo import count_known_issues

    before = count_known_issues(db_path=db_path)
    for item in data:
        add_known_issue(
            title=item["title"],
            description=item["description"],
            make=item.get("make"),
            model=item.get("model"),
            year_start=item.get("year_start"),
            year_end=item.get("year_end"),
            severity=item.get("severity", "medium"),
            symptoms=item.get("symptoms", []),
            dtc_codes=item.get("dtc_codes", []),
            causes=item.get("causes", []),
            fix_procedure=item.get("fix_procedure"),
            parts_needed=item.get("parts_needed", []),
            estimated_hours=item.get("estimated_hours"),
            db_path=db_path,
            # Phase 211: files that predate provenance carry no key and
            # load as `unverified` — a true statement about their origin.
            source=item.get("source", "unverified"),
            # Phase 255: which machines the row's content holds for. Absent
            # in every file written before 255, which loads as unscoped.
            applicability=item.get("applicability"),
        )

    return count_known_issues(db_path=db_path) - before
