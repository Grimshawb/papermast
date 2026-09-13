"""DuckDB staging warehouse for Open Library dump data."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb


SCHEMA_VERSION = 1
CLASSIFICATION_VERSION = 1
RETRIEVAL_DOCUMENT_VERSION = 1

# These expressions deliberately use word boundaries so "nonfiction" does not
# satisfy "fiction". They are broad candidate-generation rules; confidence and
# audit strata preserve the distinction between explicit and inferred evidence.
EXPLICIT_FICTION_PATTERN = r"(^|[^a-z])fiction([^a-z]|$)"
NARRATIVE_SUBJECT_PATTERN = r"(^|[^a-z])(novels?|novellas?|short stories|ghost stories|love stories|detective stories|adventure stories)([^a-z]|$)"
DESCRIPTION_NARRATIVE_PATTERN = r"(^|[^a-z])(novel|novella|work of fiction|collection of short stories)([^a-z]|$)"
STRONG_NONFICTION_PATTERN = r"nonfiction|bibliograph|criticism|study and teaching|handbooks?|manuals?|textbooks?|congresses|law and legislation|government reports?"

GENRE_PATTERNS = {
    "horror": r"horror|ghost stories|gothic fiction|supernatural fiction|occult fiction|vampires?, fiction",
    "fantasy": r"fantasy|epic fiction|fairy tales|magic, fiction|imaginary (places|worlds)",
    "science-fiction": r"science fiction|space opera|cyberpunk|dystopian fiction|time travel, fiction",
    "mystery": r"mystery|detective|crime fiction|private investigators?, fiction|police procedural",
    "thriller": r"thrillers?|suspense fiction|fiction, suspense|espionage fiction|spy stories",
    "romance": r"romance|love stories|romantic fiction|man-woman relationships, fiction",
    "historical-fiction": r"historical fiction|fiction, historical",
    "literary-fiction": r"literary fiction",
    "young-adult": r"young adult fiction|teen fiction",
}


DATASET_COLUMNS = {
    "works": """
        key AS work_key,
        TRY_CAST(revision AS INTEGER) AS revision,
        TRY_CAST(last_modified AS TIMESTAMP) AS last_modified,
        json_extract_string(record, '$.title') AS title,
        json_extract_string(record, '$.subtitle') AS subtitle,
        CASE json_type(record, '$.description')
            WHEN 'VARCHAR' THEN json_extract_string(record, '$.description')
            WHEN 'OBJECT' THEN json_extract_string(record, '$.description.value')
        END AS description,
        COALESCE(CAST(json_extract(record, '$.authors') AS VARCHAR), '[]') AS authors_json,
        COALESCE(CAST(json_extract(record, '$.subjects') AS VARCHAR), '[]') AS subjects_json,
        COALESCE(CAST(json_extract(record, '$.subject_places') AS VARCHAR), '[]') AS subject_places_json,
        COALESCE(CAST(json_extract(record, '$.subject_times') AS VARCHAR), '[]') AS subject_times_json,
        COALESCE(CAST(json_extract(record, '$.subject_people') AS VARCHAR), '[]') AS subject_people_json,
        json_extract_string(record, '$.first_publish_date') AS first_publish_date,
        COALESCE(CAST(json_extract(record, '$.covers') AS VARCHAR), '[]') AS covers_json,
        COALESCE(CAST(json_extract(record, '$.original_languages') AS VARCHAR), '[]') AS original_languages_json
    """,
    "authors": """
        key AS author_key,
        TRY_CAST(revision AS INTEGER) AS revision,
        TRY_CAST(last_modified AS TIMESTAMP) AS last_modified,
        json_extract_string(record, '$.name') AS name,
        json_extract_string(record, '$.personal_name') AS personal_name,
        CASE json_type(record, '$.bio')
            WHEN 'VARCHAR' THEN json_extract_string(record, '$.bio')
            WHEN 'OBJECT' THEN json_extract_string(record, '$.bio.value')
        END AS bio,
        COALESCE(CAST(json_extract(record, '$.alternate_names') AS VARCHAR), '[]') AS alternate_names_json,
        json_extract_string(record, '$.birth_date') AS birth_date,
        json_extract_string(record, '$.death_date') AS death_date,
        COALESCE(CAST(json_extract(record, '$.remote_ids') AS VARCHAR), '{}') AS remote_ids_json
    """,
    "editions": """
        key AS edition_key,
        TRY_CAST(revision AS INTEGER) AS revision,
        TRY_CAST(last_modified AS TIMESTAMP) AS last_modified,
        json_extract_string(record, '$.title') AS title,
        json_extract_string(record, '$.subtitle') AS subtitle,
        COALESCE(CAST(json_extract(record, '$.works') AS VARCHAR), '[]') AS works_json,
        COALESCE(CAST(json_extract(record, '$.authors') AS VARCHAR), '[]') AS authors_json,
        COALESCE(CAST(json_extract(record, '$.languages') AS VARCHAR), '[]') AS languages_json,
        CASE json_type(record, '$.description')
            WHEN 'VARCHAR' THEN json_extract_string(record, '$.description')
            WHEN 'OBJECT' THEN json_extract_string(record, '$.description.value')
        END AS description,
        COALESCE(CAST(json_extract(record, '$.subjects') AS VARCHAR), '[]') AS subjects_json,
        json_extract_string(record, '$.publish_date') AS publish_date,
        COALESCE(CAST(json_extract(record, '$.publishers') AS VARCHAR), '[]') AS publishers_json,
        COALESCE(CAST(json_extract(record, '$.isbn_10') AS VARCHAR), '[]') AS isbn_10_json,
        COALESCE(CAST(json_extract(record, '$.isbn_13') AS VARCHAR), '[]') AS isbn_13_json,
        COALESCE(CAST(json_extract(record, '$.covers') AS VARCHAR), '[]') AS covers_json,
        TRY_CAST(json_extract_string(record, '$.number_of_pages') AS INTEGER) AS number_of_pages,
        json_extract_string(record, '$.physical_format') AS physical_format,
        json_extract_string(record, '$.edition_name') AS edition_name,
        json_extract_string(record, '$.ocaid') AS ocaid
    """,
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def source_metadata(path: Path) -> Dict[str, Any]:
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    metadata: Dict[str, Any] = {}
    if sidecar.is_file():
        try:
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"could not read download metadata {sidecar}: {error}") from error
    stat = path.stat()
    return {
        "filename": path.name,
        "path": str(path.resolve()),
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": metadata.get("sha256"),
        "dump_date": metadata.get("dump_date"),
    }


def source_identity(metadata: Dict[str, Any]) -> str:
    return metadata.get("sha256") or f"{metadata['filename']}:{metadata['size_bytes']}:{metadata['modified_ns']}"


def connect_database(database: Path, temporary_directory: Path, memory_limit: str, threads: int) -> duckdb.DuckDBPyConnection:
    database.parent.mkdir(parents=True, exist_ok=True)
    temporary_directory.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    connection.execute(f"SET memory_limit = {sql_string(memory_limit)}")
    connection.execute(f"SET threads = {max(1, threads)}")
    connection.execute(f"SET temp_directory = {sql_string(str(temporary_directory.resolve()))}")
    connection.execute("SET preserve_insertion_order = false")
    connection.execute("PRAGMA enable_progress_bar")
    connection.execute("SET progress_bar_time = 2000")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS import_runs (
            dataset VARCHAR PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            source_identity VARCHAR NOT NULL,
            source_filename VARCHAR NOT NULL,
            source_size_bytes UBIGINT NOT NULL,
            dump_date VARCHAR,
            imported_at_utc TIMESTAMP NOT NULL,
            row_count UBIGINT NOT NULL
        )
    """)
    return connection


def raw_dump_scan(path: Path) -> str:
    return f"""
        read_csv(
            {sql_string(str(path.resolve()))},
            delim = '\\t',
            header = false,
            quote = '',
            escape = '',
            compression = 'gzip',
            strict_mode = true,
            null_padding = false,
            maximum_line_size = 16777216,
            buffer_size = 67108864,
            columns = {{
                'record_type': 'VARCHAR',
                'key': 'VARCHAR',
                'revision': 'VARCHAR',
                'last_modified': 'VARCHAR',
                'record': 'JSON'
            }}
        )
    """


def table_exists(connection: duckdb.DuckDBPyConnection, table: str) -> bool:
    return connection.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'main' AND table_name = ?",
        [table],
    ).fetchone()[0] == 1


def imported_identity(connection: duckdb.DuckDBPyConnection, dataset: str) -> Optional[str]:
    row = connection.execute("SELECT source_identity FROM import_runs WHERE dataset = ?", [dataset]).fetchone()
    return row[0] if row else None


def ingest_dataset(
    database: Path,
    dataset: str,
    dump_path: Path,
    temporary_directory: Path,
    memory_limit: str = "12GB",
    threads: int = 8,
) -> Dict[str, Any]:
    if dataset not in DATASET_COLUMNS:
        raise ValueError(f"unsupported dataset: {dataset}")
    if not dump_path.is_file():
        raise FileNotFoundError(f"{dataset} dump does not exist: {dump_path}")
    metadata = source_metadata(dump_path)
    identity = source_identity(metadata)
    connection = connect_database(database, temporary_directory, memory_limit, threads)
    staging = f"{dataset}_next"
    try:
        if table_exists(connection, dataset) and imported_identity(connection, dataset) == identity:
            count = connection.execute(f"SELECT count(*) FROM {dataset}").fetchone()[0]
            return {"dataset": dataset, "status": "unchanged", "row_count": count, "source": metadata}

        connection.execute(f"DROP TABLE IF EXISTS {staging}")
        expected_type = f"/type/{dataset[:-1] if dataset.endswith('s') else dataset}"
        columns = DATASET_COLUMNS[dataset]
        print(f"Importing {dataset} from {dump_path.name} into {database}...", flush=True)
        connection.execute(f"""
            CREATE TABLE {staging} AS
            SELECT {columns}
            FROM {raw_dump_scan(dump_path)}
            WHERE record_type = {sql_string(expected_type)}
        """)
        count = connection.execute(f"SELECT count(*) FROM {staging}").fetchone()[0]
        if count == 0:
            raise RuntimeError(f"{dataset} import produced zero rows")

        connection.execute("BEGIN TRANSACTION")
        try:
            # A changed source invalidates every derived table. Dropping these
            # here lets rebuild_catalog safely treat an existing phase as done.
            for derived in (
                "embedding_corpus", "embedding_pilot", "retrieval_documents",
                "fiction_catalog", "fiction_review_candidates", "fiction_classifications",
                "edition_fiction_evidence",
                "catalog_candidates", "author_names", "work_edition_summary",
                "edition_works", "work_authors",
            ):
                connection.execute(f"DROP TABLE IF EXISTS {derived}")
            connection.execute(f"DROP TABLE IF EXISTS {dataset}")
            connection.execute(f"ALTER TABLE {staging} RENAME TO {dataset}")
            connection.execute("DELETE FROM import_runs WHERE dataset = ?", [dataset])
            connection.execute("""
                INSERT INTO import_runs
                (dataset, schema_version, source_identity, source_filename, source_size_bytes, dump_date, imported_at_utc, row_count)
                VALUES (?, ?, ?, ?, ?, ?, CAST(? AS TIMESTAMP), ?)
            """, [dataset, SCHEMA_VERSION, identity, metadata["filename"], metadata["size_bytes"], metadata["dump_date"], utc_now(), count])
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        connection.execute("CHECKPOINT")
        return {"dataset": dataset, "status": "imported", "row_count": count, "source": metadata}
    finally:
        connection.close()


def rebuild_catalog(database: Path, temporary_directory: Path, memory_limit: str = "16GB", threads: int = 4) -> Dict[str, Any]:
    connection = connect_database(database, temporary_directory, memory_limit, threads)
    try:
        missing = [name for name in DATASET_COLUMNS if not table_exists(connection, name)]
        if missing:
            raise RuntimeError(f"cannot merge before importing: {', '.join(missing)}")
        if not table_exists(connection, "work_authors"):
            print("Materializing work-author links...", flush=True)
            connection.execute("""
            CREATE OR REPLACE TABLE work_authors AS
            SELECT
                w.work_key,
                json_extract_string(author.value, '$.author.key') AS author_key,
                CAST(author.key AS INTEGER) AS author_position
            FROM works w, json_each(w.authors_json) author
            WHERE json_extract_string(author.value, '$.author.key') IS NOT NULL
            """)
        if not table_exists(connection, "edition_works"):
            print("Materializing edition-work links...", flush=True)
            connection.execute("""
            CREATE OR REPLACE TABLE edition_works AS
            SELECT
                e.edition_key,
                json_extract_string(work.value, '$.key') AS work_key
            FROM editions e, json_each(e.works_json) work
            WHERE json_extract_string(work.value, '$.key') IS NOT NULL
            """)
        summary_query = """
            WITH edition_features AS (
                SELECT
                    ew.work_key,
                    e.*,
                    contains(e.languages_json, '/languages/eng') AS is_english,
                    json_array_length(e.isbn_13_json) > 0 OR json_array_length(e.isbn_10_json) > 0 AS has_isbn,
                    json_array_length(e.covers_json) > 0 AS has_cover,
                    (
                        CASE WHEN contains(e.languages_json, '/languages/eng') THEN 100 ELSE 0 END
                        + CASE WHEN json_array_length(e.isbn_13_json) > 0 THEN 20 ELSE 0 END
                        + CASE WHEN json_array_length(e.covers_json) > 0 THEN 10 ELSE 0 END
                        + CASE WHEN e.description IS NOT NULL AND length(e.description) >= 100 THEN 5 ELSE 0 END
                        + CASE WHEN e.number_of_pages BETWEEN 20 AND 5000 THEN 3 ELSE 0 END
                        + CASE WHEN e.publish_date IS NOT NULL THEN 2 ELSE 0 END
                    ) AS representative_score
                FROM edition_works ew
                JOIN editions e USING (edition_key)
                WHERE hash(ew.work_key) % ? = ?
            ), summaries AS (
                SELECT
                    work_key,
                    count(*) AS edition_count,
                    count(*) FILTER (WHERE is_english) AS english_edition_count,
                    count(*) FILTER (WHERE has_isbn) AS isbn_edition_count,
                    count(*) FILTER (WHERE has_cover) AS cover_edition_count,
                    arg_max(
                        struct_pack(
                            edition_key := edition_key,
                            is_english := is_english,
                            title := title,
                            subtitle := subtitle,
                            description := description,
                            publish_date := publish_date,
                            publishers_json := publishers_json,
                            isbn_10_json := isbn_10_json,
                            isbn_13_json := isbn_13_json,
                            covers_json := covers_json,
                            number_of_pages := number_of_pages,
                            physical_format := physical_format,
                            edition_name := edition_name,
                            ocaid := ocaid
                        ),
                        CAST(representative_score AS BIGINT) * 1000000000 + COALESCE(revision, 0)
                    ) AS representative
                FROM edition_features
                GROUP BY work_key
            )
            SELECT
                * EXCLUDE (representative),
                representative.edition_key AS representative_edition_key,
                representative.is_english AS representative_is_english,
                representative.title AS representative_title,
                representative.subtitle AS representative_subtitle,
                representative.description AS representative_description,
                representative.publish_date AS representative_publish_date,
                representative.publishers_json AS representative_publishers_json,
                representative.isbn_10_json AS representative_isbn_10_json,
                representative.isbn_13_json AS representative_isbn_13_json,
                representative.covers_json AS representative_covers_json,
                representative.number_of_pages AS representative_number_of_pages,
                representative.physical_format AS representative_physical_format,
                representative.edition_name AS representative_edition_name,
                representative.ocaid AS representative_ocaid
            FROM summaries
        """
        # Partitioning by a stable hash bounds the aggregate state for very large
        # dumps. The completed staging table replaces the prior summary only after
        # every partition succeeds, so an interrupted merge remains recoverable.
        if not table_exists(connection, "work_edition_summary"):
            print("Selecting representative editions and aggregating edition evidence...", flush=True)
            partition_count = 32
            connection.execute("DROP TABLE IF EXISTS work_edition_summary_staging")
            connection.execute(
                f"CREATE TABLE work_edition_summary_staging AS {summary_query} LIMIT 0",
                [partition_count, 0],
            )
            for partition in range(partition_count):
                print(f"  edition partition {partition + 1}/{partition_count}", flush=True)
                connection.execute(
                    f"INSERT INTO work_edition_summary_staging {summary_query}",
                    [partition_count, partition],
                )
            connection.execute("ALTER TABLE work_edition_summary_staging RENAME TO work_edition_summary")

        partition_count = 32
        if not table_exists(connection, "author_names"):
            print("Resolving author names...", flush=True)
            author_query = """
                SELECT wa.work_key,
                       list(COALESCE(a.name, a.personal_name) ORDER BY wa.author_position)
                           FILTER (WHERE COALESCE(a.name, a.personal_name) IS NOT NULL) AS author_names,
                       count(*) FILTER (WHERE COALESCE(a.name, a.personal_name) IS NOT NULL) AS resolved_author_count
                FROM work_authors wa
                JOIN work_edition_summary english_work ON english_work.work_key = wa.work_key
                    AND english_work.english_edition_count > 0
                LEFT JOIN authors a USING (author_key)
                WHERE hash(wa.work_key) % ? = ?
                GROUP BY wa.work_key
            """
            connection.execute(f"CREATE TABLE author_names AS {author_query} LIMIT 0", [partition_count, 0])
            for partition in range(partition_count):
                print(f"  author partition {partition + 1}/{partition_count}", flush=True)
                connection.execute(f"INSERT INTO author_names {author_query}", [partition_count, partition])

        print("Building merged catalog candidates...", flush=True)
        candidate_query = """
            SELECT
                w.*,
                an.author_names,
                COALESCE(an.resolved_author_count, 0) AS resolved_author_count,
                wes.* EXCLUDE (work_key),
                (w.title IS NOT NULL AND length(trim(w.title)) > 0) AS has_title,
                (COALESCE(an.resolved_author_count, 0) > 0) AS has_resolved_author,
                (w.description IS NOT NULL AND length(trim(w.description)) > 0) AS has_work_description,
                (json_array_length(w.subjects_json) >= 3) AS has_three_subjects,
                (wes.english_edition_count > 0) AS has_english_edition
            FROM works w
            LEFT JOIN author_names an USING (work_key)
            LEFT JOIN work_edition_summary wes USING (work_key)
            WHERE w.title IS NOT NULL
              AND length(trim(w.title)) > 0
              AND COALESCE(an.resolved_author_count, 0) > 0
              AND wes.english_edition_count > 0
              AND (
                  (w.description IS NOT NULL AND length(trim(w.description)) > 0)
                  OR json_array_length(w.subjects_json) >= 3
                  OR wes.representative_description IS NOT NULL
              )
              AND hash(w.work_key) % ? = ?
        """
        connection.execute("DROP TABLE IF EXISTS catalog_candidates_staging")
        connection.execute(f"CREATE TABLE catalog_candidates_staging AS {candidate_query} LIMIT 0", [partition_count, 0])
        for partition in range(partition_count):
            print(f"  candidate partition {partition + 1}/{partition_count}", flush=True)
            connection.execute(f"INSERT INTO catalog_candidates_staging {candidate_query}", [partition_count, partition])
        connection.execute("DROP TABLE IF EXISTS catalog_candidates")
        connection.execute("ALTER TABLE catalog_candidates_staging RENAME TO catalog_candidates")
        connection.execute("CHECKPOINT")
        counts = {
            "works": connection.execute("SELECT count(*) FROM works").fetchone()[0],
            "authors": connection.execute("SELECT count(*) FROM authors").fetchone()[0],
            "editions": connection.execute("SELECT count(*) FROM editions").fetchone()[0],
            "work_author_links": connection.execute("SELECT count(*) FROM work_authors").fetchone()[0],
            "edition_work_links": connection.execute("SELECT count(*) FROM edition_works").fetchone()[0],
            "catalog_candidates": connection.execute("SELECT count(*) FROM catalog_candidates").fetchone()[0],
            "metadata_capable_english": connection.execute("SELECT count(*) FROM catalog_candidates").fetchone()[0],
        }
        return counts
    finally:
        connection.close()


def classify_fiction(
    database: Path,
    temporary_directory: Path,
    memory_limit: str = "16GB",
    threads: int = 4,
    seed: int = 20260826,
    sample_size: int = 50,
) -> Dict[str, Any]:
    """Build the explainable fiction catalog and return an audit report."""
    if sample_size < 1:
        raise ValueError("sample size must be positive")
    connection = connect_database(database, temporary_directory, memory_limit, threads)
    try:
        if not table_exists(connection, "catalog_candidates"):
            raise RuntimeError("cannot classify before the merged catalog exists")

        print("Collecting fiction evidence from linked editions...", flush=True)
        connection.execute("DROP TABLE IF EXISTS edition_fiction_evidence_staging")
        connection.execute("""
            CREATE TABLE edition_fiction_evidence_staging AS
            WITH evidence AS (
                SELECT
                    ew.work_key,
                    regexp_matches(lower(e.subjects_json), ?) AS explicit_fiction,
                    regexp_matches(lower(e.subjects_json), ?) AS narrative_subject,
                    e.subjects_json,
                    e.revision
                FROM editions e
                JOIN edition_works ew USING (edition_key)
                WHERE regexp_matches(lower(e.subjects_json), ?)
                   OR regexp_matches(lower(e.subjects_json), ?)
            )
            SELECT
                work_key,
                bool_or(explicit_fiction) AS explicit_fiction,
                bool_or(narrative_subject) AS narrative_subject,
                arg_max(subjects_json,
                    CAST((CASE WHEN explicit_fiction THEN 2 ELSE 0 END
                     + CASE WHEN narrative_subject THEN 1 ELSE 0 END) AS BIGINT) * 1000000000
                    + COALESCE(revision, 0)) AS evidence_subjects_json
            FROM evidence
            GROUP BY work_key
        """, [
            EXPLICIT_FICTION_PATTERN, NARRATIVE_SUBJECT_PATTERN,
            EXPLICIT_FICTION_PATTERN, NARRATIVE_SUBJECT_PATTERN,
        ])
        connection.execute("DROP TABLE IF EXISTS edition_fiction_evidence")
        connection.execute("ALTER TABLE edition_fiction_evidence_staging RENAME TO edition_fiction_evidence")

        combined_subjects = "lower(c.subjects_json || ' ' || COALESCE(efe.evidence_subjects_json, ''))"
        genre_flags = []
        genre_names = []
        for index, (genre, pattern) in enumerate(GENRE_PATTERNS.items()):
            genre_flags.append(f"regexp_matches({combined_subjects}, ?) AS genre_{index}")
            genre_names.append((genre, pattern))
        genre_list = ", ".join(
            f"CASE WHEN genre_{index} THEN '{genre}' END"
            for index, (genre, _) in enumerate(genre_names)
        )

        print("Materializing explainable fiction classifications...", flush=True)
        connection.execute("DROP TABLE IF EXISTS fiction_catalog_staging")
        query = f"""
            CREATE TABLE fiction_catalog_staging AS
            WITH signals AS (
                SELECT
                    c.*,
                    regexp_matches(lower(c.subjects_json), ?) AS work_explicit_fiction,
                    COALESCE(efe.explicit_fiction, false) AS edition_explicit_fiction,
                    regexp_matches(lower(c.subjects_json), ?) AS work_narrative_subject,
                    COALESCE(efe.narrative_subject, false) AS edition_narrative_subject,
                    regexp_matches(lower(COALESCE(c.description, c.representative_description, '')), ?) AS description_narrative,
                    regexp_matches(lower(c.subjects_json), ?) AS strong_nonfiction_conflict,
                    efe.evidence_subjects_json AS edition_evidence_subjects_json,
                    {', '.join(genre_flags)}
                FROM catalog_candidates c
                LEFT JOIN edition_fiction_evidence efe USING (work_key)
            ), classified AS (
                SELECT *,
                    (work_explicit_fiction OR edition_explicit_fiction) AS explicit_fiction,
                    (work_narrative_subject OR edition_narrative_subject) AS narrative_subject,
                    (description_narrative AND NOT strong_nonfiction_conflict) AS description_inferred,
                    list_filter([{genre_list}], item -> item IS NOT NULL) AS genres
                FROM signals
            )
            SELECT
                work_key, title, subtitle, author_names,
                COALESCE(description, representative_description) AS description,
                subjects_json AS work_subjects_json,
                edition_evidence_subjects_json,
                genres,
                work_explicit_fiction, edition_explicit_fiction,
                work_narrative_subject, edition_narrative_subject,
                description_inferred, strong_nonfiction_conflict,
                CASE
                    WHEN work_explicit_fiction OR edition_explicit_fiction THEN 'high'
                    WHEN work_narrative_subject OR edition_narrative_subject THEN 'medium'
                    ELSE 'review'
                END AS fiction_confidence,
                CASE
                    WHEN work_explicit_fiction OR edition_explicit_fiction THEN 'explicit_subject'
                    WHEN work_narrative_subject OR edition_narrative_subject THEN 'narrative_subject'
                    ELSE 'description_inference'
                END AS primary_evidence,
                representative_edition_key, representative_title,
                representative_publish_date, representative_covers_json,
                representative_isbn_10_json, representative_isbn_13_json,
                representative_number_of_pages, first_publish_date,
                edition_count, english_edition_count, cover_edition_count,
                isbn_edition_count,
                ((CASE WHEN COALESCE(description, representative_description) IS NOT NULL THEN 40 ELSE 0 END)
                 + CASE WHEN cover_edition_count > 0 THEN 20 ELSE 0 END
                 + CASE WHEN first_publish_date IS NOT NULL OR representative_publish_date IS NOT NULL THEN 15 ELSE 0 END
                 + CASE WHEN isbn_edition_count > 0 THEN 10 ELSE 0 END
                 + CASE WHEN json_array_length(subjects_json) >= 3 THEN 15 ELSE 0 END) AS metadata_quality_score,
                ? AS classification_version
            FROM classified
            WHERE explicit_fiction OR narrative_subject OR description_inferred
        """
        parameters = [
            EXPLICIT_FICTION_PATTERN,
            NARRATIVE_SUBJECT_PATTERN,
            DESCRIPTION_NARRATIVE_PATTERN,
            STRONG_NONFICTION_PATTERN,
        ] + [pattern for _, pattern in genre_names] + [CLASSIFICATION_VERSION]
        connection.execute(query, parameters)
        connection.execute("DROP TABLE IF EXISTS fiction_catalog")
        connection.execute("DROP TABLE IF EXISTS fiction_review_candidates")
        connection.execute("DROP TABLE IF EXISTS fiction_classifications")
        connection.execute("ALTER TABLE fiction_catalog_staging RENAME TO fiction_classifications")
        # Only explicit, non-conflicting subject evidence is approved in v1.
        # Narrative and description inference remain available for human audit.
        connection.execute("""
            CREATE TABLE fiction_catalog AS
            SELECT * FROM fiction_classifications
            WHERE fiction_confidence = 'high' AND NOT strong_nonfiction_conflict
        """)
        connection.execute("""
            CREATE TABLE fiction_review_candidates AS
            SELECT * FROM fiction_classifications
            WHERE fiction_confidence <> 'high' OR strong_nonfiction_conflict
        """)
        connection.execute("CHECKPOINT")

        count_rows = connection.execute("""
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE fiction_confidence = 'high') AS high,
                count(*) FILTER (WHERE fiction_confidence = 'medium') AS medium,
                count(*) FILTER (WHERE fiction_confidence = 'review') AS review,
                count(*) FILTER (WHERE description IS NOT NULL) AS with_description,
                count(*) FILTER (WHERE description IS NULL) AS without_description,
                count(*) FILTER (WHERE len(genres) = 0) AS general_unclassified,
                count(*) FILTER (WHERE len(genres) > 1) AS multi_genre
            FROM fiction_classifications
        """).fetchone()
        count_names = [item[0] for item in connection.description]
        totals = dict(zip(count_names, count_rows))
        totals["accepted"] = connection.execute("SELECT count(*) FROM fiction_catalog").fetchone()[0]
        totals["review_candidates"] = connection.execute("SELECT count(*) FROM fiction_review_candidates").fetchone()[0]

        genre_counts = {
            genre: connection.execute(
                "SELECT count(*) FROM fiction_catalog WHERE list_contains(genres, ?)", [genre]
            ).fetchone()[0]
            for genre in GENRE_PATTERNS
        }

        sample_columns = """
            work_key, title, author_names, fiction_confidence, primary_evidence,
            genres, metadata_quality_score, work_subjects_json,
            edition_evidence_subjects_json, left(description, 500) AS description_excerpt
        """
        strata = {
            "high_explicit": "fiction_confidence = 'high'",
            "medium_narrative": "fiction_confidence = 'medium'",
            "review_description_inferred": "fiction_confidence = 'review'",
            "without_description": "description IS NULL",
            "strong_nonfiction_conflict": "strong_nonfiction_conflict",
            "multi_genre": "len(genres) > 1",
            "general_unclassified": "len(genres) = 0",
        }
        samples: Dict[str, Any] = {}
        for name, predicate in strata.items():
            result = connection.execute(f"""
                SELECT {sample_columns}
                FROM fiction_classifications
                WHERE {predicate}
                ORDER BY hash(work_key || ?)
                LIMIT ?
            """, [str(seed), sample_size])
            columns = [item[0] for item in result.description]
            samples[name] = [dict(zip(columns, row)) for row in result.fetchall()]
        for genre in GENRE_PATTERNS:
            result = connection.execute(f"""
                SELECT {sample_columns}
                FROM fiction_classifications
                WHERE list_contains(genres, ?)
                ORDER BY hash(work_key || ?)
                LIMIT ?
            """, [genre, str(seed), sample_size])
            columns = [item[0] for item in result.description]
            samples[f"genre_{genre}"] = [dict(zip(columns, row)) for row in result.fetchall()]

        result = connection.execute("""
            SELECT c.work_key, c.title, c.author_names,
                   c.subjects_json AS work_subjects_json,
                   left(COALESCE(c.description, c.representative_description), 500) AS description_excerpt
            FROM catalog_candidates c
            LEFT JOIN fiction_classifications f USING (work_key)
            WHERE f.work_key IS NULL
              AND COALESCE(c.description, c.representative_description) IS NOT NULL
            ORDER BY hash(c.work_key || ?)
            LIMIT ?
        """, [str(seed), sample_size])
        columns = [item[0] for item in result.description]
        samples["excluded_with_description"] = [dict(zip(columns, row)) for row in result.fetchall()]

        return {
            "schema_version": 1,
            "classification_version": CLASSIFICATION_VERSION,
            "generated_at_utc": utc_now(),
            "database": str(database.resolve()),
            "options": {"seed": seed, "sample_size": sample_size},
            "rules": {
                "explicit_fiction_pattern": EXPLICIT_FICTION_PATTERN,
                "narrative_subject_pattern": NARRATIVE_SUBJECT_PATTERN,
                "description_narrative_pattern": DESCRIPTION_NARRATIVE_PATTERN,
                "strong_nonfiction_pattern": STRONG_NONFICTION_PATTERN,
                "genre_patterns": GENRE_PATTERNS,
            },
            "totals": totals,
            "genre_counts": genre_counts,
            "samples": samples,
            "limitations": [
                "Description inference is a review tier, not a verified fiction label.",
                "Literary fiction and young adult are under-labelled in Open Library subjects.",
                "Genre counts overlap because a work may have multiple genres.",
            ],
        }
    finally:
        connection.close()


def prepare_retrieval_documents(
    database: Path,
    temporary_directory: Path,
    memory_limit: str = "16GB",
    threads: int = 4,
    seed: int = 20260826,
    sample_size: int = 50,
) -> Dict[str, Any]:
    """Build deterministic model-ready text without generating embeddings."""
    if sample_size < 1:
        raise ValueError("sample size must be positive")
    connection = connect_database(database, temporary_directory, memory_limit, threads)
    try:
        if not table_exists(connection, "fiction_catalog"):
            raise RuntimeError("cannot prepare retrieval documents before fiction classification")
        print("Cleaning subjects and constructing retrieval documents...", flush=True)
        connection.execute("DROP TABLE IF EXISTS retrieval_documents_staging")
        connection.execute("""
            CREATE TABLE retrieval_documents_staging AS
            WITH raw_subjects AS (
                SELECT f.work_key, json_extract_string(s.value, '$') AS subject
                FROM fiction_catalog f, json_each(f.work_subjects_json) s
                UNION ALL
                SELECT f.work_key, json_extract_string(s.value, '$') AS subject
                FROM fiction_catalog f, json_each(COALESCE(f.edition_evidence_subjects_json, '[]')) s
            ), normalized_subjects AS (
                SELECT DISTINCT
                    work_key,
                    trim(regexp_replace(
                        regexp_replace(lower(subject), '\\s*(--|/)\\s*', ', ', 'g'),
                        '\\s+', ' ', 'g'
                    ), ' .,;:/') AS subject
                FROM raw_subjects
                WHERE subject IS NOT NULL
            ), useful_subjects AS (
                SELECT work_key, subject
                FROM normalized_subjects
                WHERE length(subject) BETWEEN 2 AND 120
                  AND subject NOT IN (
                      'fiction', 'fiction, general', 'general', 'accessible book',
                      'protected daisy', 'in library', 'large type books',
                      'translations into english', 'internet archive wishlist'
                  )
                  AND NOT regexp_matches(subject,
                      '^(nyt|new york times bestseller|open library staff picks|reading level|grade [0-9])')
            ), subject_lists AS (
                SELECT
                    work_key,
                    list_slice(
                        list(subject ORDER BY length(subject) DESC, subject),
                        1, 25
                    ) AS cleaned_subjects
                FROM useful_subjects
                GROUP BY work_key
            ), cleaned AS (
                SELECT
                    f.*,
                    COALESCE(sl.cleaned_subjects, []::VARCHAR[]) AS cleaned_subjects,
                    CASE WHEN f.description IS NULL THEN NULL ELSE
                        left(trim(regexp_replace(
                            regexp_replace(f.description, '<[^>]+>', ' ', 'g'),
                            '\\s+', ' ', 'g'
                        )), 3000)
                    END AS cleaned_description
                FROM fiction_catalog f
                LEFT JOIN subject_lists sl USING (work_key)
            ), documents AS (
                SELECT
                    work_key,
                    concat_ws('\n',
                        'Title: ' || trim(regexp_replace(title, '\\s+', ' ', 'g'))
                            || COALESCE(': ' || NULLIF(trim(regexp_replace(subtitle, '\\s+', ' ', 'g')), ''), ''),
                        'Author: ' || array_to_string(
                            list_transform(author_names, item -> trim(regexp_replace(item, '\\s+', ' ', 'g'))),
                            '; '
                        ),
                        CASE WHEN len(genres) > 0
                            THEN 'Genres: ' || array_to_string(genres, '; ') END,
                        CASE WHEN len(cleaned_subjects) > 0
                            THEN 'Subjects: ' || array_to_string(cleaned_subjects, '; ') END,
                        CASE WHEN cleaned_description IS NOT NULL AND cleaned_description <> ''
                            THEN 'Description: ' || cleaned_description END
                    ) AS embedding_text,
                    cleaned_subjects,
                    cleaned_description,
                    CASE
                        WHEN cleaned_description IS NOT NULL AND len(cleaned_subjects) >= 3 THEN 'rich'
                        WHEN cleaned_description IS NOT NULL THEN 'described'
                        ELSE 'subject_only'
                    END AS retrieval_quality,
                    metadata_quality_score,
                    genres,
                    title,
                    author_names,
                    representative_edition_key,
                    representative_covers_json,
                    representative_isbn_10_json,
                    representative_isbn_13_json,
                    ? AS document_version
                FROM cleaned
            )
            SELECT *, sha256(embedding_text) AS document_hash
            FROM documents
        """, [RETRIEVAL_DOCUMENT_VERSION])
        invalid = connection.execute("""
            SELECT count(*) FROM retrieval_documents_staging
            WHERE embedding_text IS NULL OR length(trim(embedding_text)) = 0
               OR document_hash IS NULL
        """).fetchone()[0]
        expected = connection.execute("SELECT count(*) FROM fiction_catalog").fetchone()[0]
        actual = connection.execute("SELECT count(*) FROM retrieval_documents_staging").fetchone()[0]
        if invalid or actual != expected:
            raise RuntimeError(
                f"retrieval document validation failed: expected={expected}, actual={actual}, invalid={invalid}"
            )
        connection.execute("DROP TABLE IF EXISTS retrieval_documents")
        connection.execute("ALTER TABLE retrieval_documents_staging RENAME TO retrieval_documents")
        connection.execute("DROP TABLE IF EXISTS embedding_corpus")
        connection.execute("DROP TABLE IF EXISTS embedding_pilot")
        connection.execute("CHECKPOINT")

        result = connection.execute("""
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE retrieval_quality = 'rich') AS rich,
                count(*) FILTER (WHERE retrieval_quality = 'described') AS described,
                count(*) FILTER (WHERE retrieval_quality = 'subject_only') AS subject_only,
                count(*) FILTER (WHERE len(cleaned_subjects) = 0) AS without_useful_subjects,
                count(*) FILTER (WHERE length(embedding_text) > 4000) AS over_4000_characters,
                count(DISTINCT document_hash) AS distinct_documents,
                count(*) - count(DISTINCT document_hash) AS duplicate_document_texts,
                min(length(embedding_text)) AS min_characters,
                round(avg(length(embedding_text)), 1) AS average_characters,
                max(length(embedding_text)) AS max_characters
            FROM retrieval_documents
        """)
        totals = dict(zip([item[0] for item in result.description], result.fetchone()))
        length_distribution = {
            row[0]: row[1]
            for row in connection.execute("""
                SELECT CASE
                    WHEN length(embedding_text) < 250 THEN '<250'
                    WHEN length(embedding_text) < 500 THEN '250-499'
                    WHEN length(embedding_text) < 1000 THEN '500-999'
                    WHEN length(embedding_text) < 2000 THEN '1000-1999'
                    WHEN length(embedding_text) < 3000 THEN '2000-2999'
                    ELSE '3000+'
                END bucket, count(*)
                FROM retrieval_documents GROUP BY bucket ORDER BY min(length(embedding_text))
            """).fetchall()
        }
        subject_distribution = {
            row[0]: row[1]
            for row in connection.execute("""
                SELECT CASE
                    WHEN len(cleaned_subjects) = 0 THEN '0'
                    WHEN len(cleaned_subjects) <= 5 THEN '1-5'
                    WHEN len(cleaned_subjects) <= 10 THEN '6-10'
                    WHEN len(cleaned_subjects) <= 20 THEN '11-20'
                    ELSE '21-25'
                END bucket, count(*)
                FROM retrieval_documents GROUP BY bucket ORDER BY min(len(cleaned_subjects))
            """).fetchall()
        }
        strata = {
            "rich": "retrieval_quality = 'rich'",
            "described": "retrieval_quality = 'described'",
            "subject_only": "retrieval_quality = 'subject_only'",
            "without_useful_subjects": "len(cleaned_subjects) = 0",
            "longest": "true",
        }
        samples: Dict[str, Any] = {}
        for name, predicate in strata.items():
            order = "length(embedding_text) DESC, work_key" if name == "longest" else "hash(work_key || ?)"
            parameters: list[Any] = [sample_size] if name == "longest" else [str(seed), sample_size]
            result = connection.execute(f"""
                SELECT work_key, retrieval_quality, document_hash,
                       cleaned_subjects, embedding_text
                FROM retrieval_documents
                WHERE {predicate}
                ORDER BY {order}
                LIMIT ?
            """, parameters)
            columns = [item[0] for item in result.description]
            samples[name] = [dict(zip(columns, row)) for row in result.fetchall()]
        return {
            "schema_version": 1,
            "document_version": RETRIEVAL_DOCUMENT_VERSION,
            "generated_at_utc": utc_now(),
            "database": str(database.resolve()),
            "options": {"seed": seed, "sample_size": sample_size},
            "construction": {
                "maximum_subjects": 25,
                "maximum_description_characters": 3000,
                "fields": ["title", "author", "genres", "subjects", "description"],
                "hash": "SHA-256 of embedding_text",
            },
            "totals": totals,
            "text_length_distribution": length_distribution,
            "subject_count_distribution": subject_distribution,
            "samples": samples,
            "limitations": [
                "Character counts are not model token counts.",
                "Document preparation does not generate or select an embedding model.",
                "Subject cleanup is deterministic and preserves the original source fields elsewhere in DuckDB.",
            ],
        }
    finally:
        connection.close()


def catalog_status(database: Path) -> Dict[str, Any]:
    if not database.is_file():
        raise FileNotFoundError(f"catalog database does not exist: {database}")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        tables = {
            row[0]: row[1]
            for row in connection.execute("""
                SELECT table_name, estimated_size
                FROM duckdb_tables()
                WHERE schema_name = 'main'
                ORDER BY table_name
            """).fetchall()
        }
        imports = [
            dict(zip([item[0] for item in connection.description], row))
            for row in connection.execute("SELECT * FROM import_runs ORDER BY dataset").fetchall()
        ] if "import_runs" in tables else []
        return {"database": str(database.resolve()), "size_bytes": database.stat().st_size, "tables": tables, "imports": imports}
    finally:
        connection.close()
