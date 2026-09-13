# Open Library local catalog pipeline

This local Python tool downloads and profiles Open Library dumps, then ingests
compact work, author, and edition data into a local DuckDB warehouse. Every gzip
source is streamed directly; expanded dump files are never created. Generated
data belongs under `.data/openlibrary/`, which Git ignores.

The profiler uses `orjson` for the per-record parsing hot path. The dump is already one
complete JSON object per line, so incremental JSON parsers would add complexity
without avoiding any material buffering.

DuckDB performs the durable bulk ingestion and joins. The warehouse retains the
bibliographic fields needed for future selection experiments, so changing the
catalog ranking does not require rereading the compressed dumps.

The profiler measures the source data; its qualification funnel is not the final
PaperMast catalog policy. Author-name resolution, English-edition filtering, and
representative-edition selection require the later authors and editions phases.

## Set up the local environment

**Mac** — download each source from the repository root:

```bash
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .data/openlibrary/.venv
.data/openlibrary/.venv/bin/python -m pip install \
  -r tools/openlibrary-import/requirements.txt
```

The virtual environment is stored with the ignored local data rather than in
the tracked source tree. The pipeline is verified on Python 3.12; do not use
Apple's end-of-life `/usr/bin/python3` (currently Python 3.9 on this Mac).

## Download and verify

**Mac** — from the repository root:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  download \
  --dump works \
  --output .data/openlibrary

.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  download \
  --dump authors \
  --output .data/openlibrary

.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  download \
  --dump editions \
  --output .data/openlibrary
```

The command resolves the dated archive URL before choosing a partial filename,
so a partial file from an older month cannot be appended to a newer dump. It
uses HTTP range requests to resume that dated `.part` file, calculates SHA-256
and MD5 together in one pass, and verifies the archive's MD5 when Internet
Archive metadata is available. Download metadata is written beside the dump as
`<dump>.metadata.json`.

## Profile

**Mac** — replace the filename with the resolved dated filename printed by the
download command:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  profile \
  --input .data/openlibrary/ol_dump_works_YYYY-MM-DD.txt.gz \
  --output .data/openlibrary/reports \
  --seed 20260826
```

Progress is printed every 100,000 rows. The command writes matching JSON and
Markdown reports atomically. An interrupted profile starts again from row one.

## Build the local DuckDB warehouse

**Mac** — ingest each dated dump exactly once. Substitute the filenames printed
by the download commands:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  ingest --dataset works \
  --input .data/openlibrary/ol_dump_works_YYYY-MM-DD.txt.gz \
  --database .data/openlibrary/catalog.duckdb

.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  ingest --dataset authors \
  --input .data/openlibrary/ol_dump_authors_YYYY-MM-DD.txt.gz \
  --database .data/openlibrary/catalog.duckdb

.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  ingest --dataset editions \
  --input .data/openlibrary/ol_dump_editions_YYYY-MM-DD.txt.gz \
  --database .data/openlibrary/catalog.duckdb
```

Each import records the source checksum in `import_runs`. Rerunning a command
with the same source is a quick no-op. A changed source is built in a staging
table and replaces the prior table only after the scan succeeds.

After all three imports complete, materialize reusable relationships,
representative-edition choices, and merged candidates:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  merge \
  --database .data/openlibrary/catalog.duckdb
```

The representative edition favors English editions, then ISBN, cover,
description, sensible page count, and publication date. This is an inspectable
starting rule, not the final catalog ranking.

Large grouping phases are split into 32 deterministic work-key partitions to
bound memory. Completed link and edition-summary tables are reused after an
interrupted merge; candidate output is staged and promoted only after every
partition succeeds. The measured July 2026 build used the default 16 GB memory
limit and four DuckDB workers on the Mac.

Check the database at any point:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  status \
  --database .data/openlibrary/catalog.duckdb

ls -lh .data/openlibrary/catalog.duckdb
du -sh .data/openlibrary
```

## Classify and audit fiction

**Mac** — materialize the conservative fiction catalog and deterministic audit
samples after `merge` succeeds:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  classify \
  --database .data/openlibrary/catalog.duckdb \
  --output .data/openlibrary/reports \
  --seed 20260826 \
  --sample-size 50
```

The classification is explainable and versioned. `fiction_classifications`
contains every rule-generated candidate and its evidence. `fiction_catalog`
contains only explicit work- or edition-subject fiction without a strong
nonfiction conflict. `fiction_review_candidates` quarantines narrative-subject,
description-inferred, and conflicting records for inspection rather than
silently treating them as approved fiction. Genre assignments are multi-valued;
general fiction is not forced into one of PaperMast's genres.

The command atomically writes `fiction-classification-audit.json` and
`fiction-classification-audit.md`. Rerunning with the same seed produces the
same samples. Importing a changed source dump invalidates all merged and
classification tables so stale derived data cannot survive a source update.

## Prepare retrieval documents

**Mac** — construct the exact text a future local embedding model will receive:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  prepare-documents \
  --database .data/openlibrary/catalog.duckdb \
  --output .data/openlibrary/reports \
  --seed 20260826 \
  --sample-size 50
```

This command does not generate embeddings or contact an external service. It
normalizes and deduplicates subjects, removes generic cataloging noise, caps the
useful subject list at 25, strips HTML and normalizes whitespace in descriptions,
and caps descriptions at 3,000 characters. The resulting `retrieval_documents`
table contains one versioned row per approved fiction work, its exact
`embedding_text`, a retrieval-quality tier, and a SHA-256 document hash. The
hash allows a later resumable embedding job to regenerate only changed text.

Construction statistics and deterministic samples are written to
`retrieval-documents-report.json` and `retrieval-documents-report.md`.

## Run the local BGE pilot

The embedding dependencies are separate from the import dependencies because
PyTorch and Sentence Transformers are substantially larger:

```bash
.data/openlibrary/.venv/bin/python -m pip install \
  -r tools/openlibrary-import/requirements-embeddings.txt
```

**Mac** — select a stratified 25,000-work pilot, generate local normalized BGE
vectors, and run the fixed query suite:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/embedding_pilot.py \
  --database .data/openlibrary/catalog.duckdb \
  --output .data/openlibrary/embedding-pilot \
  --size 25000 \
  --seed 20260826 \
  --batch-size 128
```

The pilot pins `BAAI/bge-small-en-v1.5` to the exact revision recorded in the
script, uses Apple MPS when available, and writes float32 384-dimensional
vectors plus matching metadata and checksums. Existing vectors are reused only
when the ordered work keys and document hashes still match, so rerunning the
evaluation does not repeat model inference. Query embeddings use BGE's required
retrieval instruction; vectors and embedding internals are never sent to an
LLM.

Review `bge-pilot-report.md` in the output directory. Its automated genre metric
uses incomplete derived genre labels and is diagnostic rather than ground
truth; the per-query candidate lists are the more useful evaluation artifact.

## Embed the complete fiction catalog

After accepting the pilot results, generate vectors for every row in
`retrieval_documents`:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/embed_full_catalog.py \
  --database .data/openlibrary/catalog.duckdb \
  --output .data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1 \
  --shard-size 10000 \
  --batch-size 128 \
  --cooldown-seconds 10
```

This runs entirely on the Mac. It does not call an LLM, upload book text, or
require Qdrant. The command pins the same BGE model revision as the pilot,
materializes a stable work-key ordering in DuckDB, and writes normalized
384-dimensional float32 vectors in 10,000-record shards. A corresponding JSONL
file retains the work key, document hash, and retrieval metadata for each
vector.

`--cooldown-seconds` is optional. A short pause between shards reduces sustained
thermal load on a laptop without changing the vectors or their compatibility.

The atomic `manifest.json` records the corpus identity, model identity, shard
ranges, and SHA-256 checksums. Rerunning the identical command verifies existing
completed shards and resumes at the first unfinished shard. If the source
documents or material settings differ, use a new output directory rather than
mixing incompatible vectors. These files are the portable input for a later
Qdrant collection; Qdrant is not needed to generate or validate them.

## Load and search the local Qdrant collection

Qdrant uses a separate dependency set. The Python client and server are pinned
to matching compatible releases:

```bash
.data/openlibrary/.venv/bin/python -m pip install \
  -r tools/openlibrary-import/requirements-qdrant.txt
```

**Mac** — start Qdrant as part of PaperMast's standard local dependency stack:

```bash
docker volume create papermast-openlibrary-qdrant-storage
docker volume create papermast-openlibrary-qdrant-snapshots
docker compose up -d qdrant
curl --fail http://127.0.0.1:6333/healthz
```

The volume-creation commands are idempotent. These catalog volumes are declared
external so routine root-stack cleanup cannot accidentally delete the expensive
local import. Existing volumes created by the earlier isolated Compose file are
reused directly.

Only loopback ports `6333` and `6334` are published. Qdrant is capped at two CPU
cores and 6 GiB of memory, and anonymous Qdrant telemetry is disabled. Its live
database and snapshots use Docker-managed Linux volumes because Qdrant warns
that Docker Desktop's macOS FUSE bind mounts can corrupt its database through
incompatible caching behavior. Generated reports and resumable import state
remain under the ignored `.data/openlibrary` tree.

**Mac** — import every checksummed embedding shard:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/qdrant_catalog.py \
  import \
  --source .data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1 \
  --batch-size 128 \
  --cooldown-seconds 5
```

Point IDs are deterministic UUIDs derived from Open Library work keys. If a
request succeeds but the process stops before recording its shard, retrying is
safe because Qdrant upserts the same IDs. The importer validates source
checksums, advances its state atomically after each shard, and defers HNSW index
construction until upload finishes. Payload indexes for genre, retrieval tier,
and metadata quality are created before upload.

Check readiness. Search evaluation should wait for `status: green` and for the
indexed-vector count to equal the point count:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/qdrant_catalog.py \
  status \
  --source .data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1
```

Embed a natural-language query locally and retrieve real catalog works:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/qdrant_catalog.py \
  search "A cozy mystery in a small town" \
  --source .data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1 \
  --limit 50
```

An optional exact `--genre mystery` filter uses the Qdrant payload index. Raw
retrieval normally remains unfiltered so the future LLM can consider surprising
cross-genre candidates while applying the original request's constraints.

Run the fixed 16-query diagnostic suite:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/qdrant_catalog.py \
  evaluate \
  --source .data/openlibrary/embeddings/bge-small-en-v1.5-doc-v1 \
  --output .data/openlibrary/reports
```

Create an immutable collection snapshot in Qdrant's managed snapshot volume:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/qdrant_catalog.py \
  snapshot
```

Stop Qdrant without deleting its database or snapshots:

```bash
docker compose stop qdrant
```

To remove the Qdrant container while preserving the catalog volume:

```bash
docker compose rm --stop qdrant
```

The external Qdrant volumes survive even `docker compose down --volumes`. Delete
them only with explicit `docker volume rm` commands after confirming that losing
the complete local catalog and snapshots is intentional.

## Rerank local candidates with Gemini

The Gemini experiment retrieves 200 Qdrant results and assembles a diversified
40-work candidate pool. Gemini receives the original reader request plus those
40 deduplicated public catalog records from DuckDB. Placeholder titles such as
`Untitled` are removed first.
It never receives embeddings, similarity scores, or retrieval rank. Its
structured response is rejected unless it contains the requested number of
distinct work keys and every key came from those candidates.

High-confidence negative constraints are handled before reranking. Recognized
genre and author exclusions are removed from the text embedded for retrieval,
then enforced as hard local filters. A request such as “like Stephen King
without Stephen King” uses the centroid of that author's rich catalog works as
its retrieval vector, then removes the author and matching surname titles. The
pool favors described records, limits repeated authors and anthologies, and
caps subject-only records when enough richer alternatives exist. The original
reader request is still sent to Gemini unchanged.

Install the pinned SDK dependencies:

```bash
.data/openlibrary/.venv/bin/python -m pip install \
  -r tools/openlibrary-import/requirements-gemini.txt
```

Store the key in `.data/openlibrary/gemini.env`, which is already ignored by
Git, and restrict the file to the current Mac user:

```dotenv
GEMINI_API_KEY=replace_with_the_real_key
```

```bash
chmod 600 .data/openlibrary/gemini.env
```

Run one end-to-end recommendation:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/gemini_librarian.py \
  recommend "Something creepy and historical, but not outright horror" \
  --output .data/openlibrary/reports/gemini-single-request.json
```

The CLI pins the stable `gemini-3.5-flash-lite` model and records token usage,
latency, candidate count, hydrated recommendations, and a paid-tier cost
estimate. The evaluation command defaults to only one request to protect a free
tier. It writes an atomic checkpoint after each completed query. Increase the
cap explicitly only when intended; `--max-queries 16` runs the complete fixed
suite:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/gemini_librarian.py \
  evaluate --max-queries 1
```

The September 2026 full-suite run completed all 16 requests without a rate-limit
failure. It used 107,600 input tokens and 4,883 output tokens, with 1.76 seconds
mean Gemini latency. The paid-tier equivalent was approximately $0.0445; the
actual free-tier charge was zero.

That first run exposed that embedding similarity does not reliably understand
negative constraints. The subsequent constraint-aware implementation can be
tested locally without using Gemini quota:

```bash
HF_HOME=.data/openlibrary/huggingface \
.data/openlibrary/.venv/bin/python tools/openlibrary-import/gemini_librarian.py \
  evaluate-local --max-queries 16
```

The resulting `constraint-aware-retrieval-evaluation.json` records all 40
candidates per query, extracted constraints, metadata mix, anthology count, and
constraint violations. The accepted run produced zero excluded-genre and zero
excluded-author violations. Targeted Gemini regressions then corrected the
previous “not horror,” accessible-science-fiction, and “without Stephen King”
failures. Do not treat exact derived genre-label counts as ground truth because
Open Library classifications are incomplete.

Google states that free-tier inputs may be used to improve its products. The
current tests send only synthetic prompts and public Open Library metadata; do
not use real visitor prompts until the project's privacy disclosure and chosen
Gemini billing/data-use tier have been reviewed.

## Finalize the backend catalog artifact

Create the compact runtime-data artifact after the embedding manifest and
Qdrant collection are complete:

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/finalize_catalog.py
```

This exports `.data/openlibrary/production/catalog-v1/fiction-catalog.parquet`
with Zstandard compression and writes a matching `manifest.json`. The artifact
contains catalog metadata needed at runtime but omits embedding text and all
research-only warehouse tables. The manifest validates and records the catalog
row identity, SHA-256 checksum, embedding model/revision, Qdrant collection
configuration and counts, and latest Qdrant snapshot.

The accepted catalog contains 676,258 unique works in a 122.3 MiB Parquet file.
It matches 676,258 completed embeddings and a green, fully indexed Qdrant
collection. DuckDB remains the rebuild and audit source; the Parquet file is the
portable, versioned source for building a production Qdrant collection, not a
live application database. The runtime design deliberately avoids duplicating
the complete Open Library catalog in MySQL.

Once the imports and merge have been verified, the three `.txt.gz` sources may
be deleted to reclaim their compressed space. Keep their metadata sidecars if
you want a small record of source checksums. Deleting a dump does not affect the
warehouse, but rebuilding a changed source table later requires downloading
that dump again.

## Inspect reports

**Mac**:

```bash
ls -lh .data/openlibrary/reports
less .data/openlibrary/reports/ol_dump_works_YYYY-MM-DD-profile.md
```

## Run tests

**Mac**:

```bash
.data/openlibrary/.venv/bin/python -m unittest discover \
  -s tools/openlibrary-import/tests \
  -p 'test_*.py' \
  -v
```

## Replace with a newer monthly dump

**Mac** — download first, successfully ingest and merge the new dated files, and
only then remove previous dumps explicitly. Never delete a `.part` file while a
download is running.

```bash
.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  download \
  --dump works \
  --output .data/openlibrary

.data/openlibrary/.venv/bin/python tools/openlibrary-import/openlibrary_import.py \
  profile \
  --input .data/openlibrary/ol_dump_works_NEW-DATE.txt.gz \
  --output .data/openlibrary/reports \
  --seed 20260826

rm .data/openlibrary/ol_dump_works_OLD-DATE.txt.gz
rm .data/openlibrary/ol_dump_works_OLD-DATE.txt.gz.metadata.json
```

The final two commands are intentionally explicit because dump deletion is not
recoverable without downloading the source again.

## Production-shaped local librarian service

The runtime experiment keeps catalog metadata with each Qdrant point so the
long-running recommendation service does not need the 28 GB DuckDB warehouse.
It uses FastEmbed's quantized ONNX build of `BAAI/bge-small-en-v1.5`; a local
compatibility check against the pinned PyTorch model produced cosine similarity
of `0.9999989`. PyTorch remains part of the offline embedding toolchain, but is
not imported by the HTTP service.

Install the service dependencies on the **Mac**:

```bash
.data/openlibrary/.venv/bin/python -m pip install \
  -r tools/openlibrary-import/requirements-service.txt
```

Build the separate, resumable runtime collection without modifying the original
evaluation collection:

```bash
.data/openlibrary/.venv/bin/python \
  tools/openlibrary-import/runtime_collection.py build
```

Check until `status` is `green` and `indexed_vectors_count` is `676258`:

```bash
.data/openlibrary/.venv/bin/python \
  tools/openlibrary-import/runtime_collection.py status
```

Start the private service on loopback only:

```bash
.data/openlibrary/.venv/bin/python -m uvicorn librarian_service:app \
  --app-dir tools/openlibrary-import --host 127.0.0.1 --port 8091 --workers 1
```

Inspect readiness and its current resident memory:

```bash
curl --fail --silent http://127.0.0.1:8091/health/ready | python3 -m json.tool
```

Request a recommendation (this makes one Gemini API request):

```bash
curl --fail --silent http://127.0.0.1:8091/recommend \
  --header 'Content-Type: application/json' \
  --data '{"query":"Something funny and weird.","result_count":5}' \
  | python3 -m json.tool
```

Only the ASP.NET API will be allowed to call this service when it is added to
the production Compose network. Neither the service nor Qdrant should publish a
production host port.

### Run the containerized local service

The Docker build context excludes `.data`, so the dumps and DuckDB warehouse
are never copied or sent to the Docker builder. The exact ONNX model revision
is baked into the image; the local Compose file mounts only the private Gemini
environment file as a read-only input.

Build and start Qdrant plus the librarian on the **Mac**:

```bash
docker compose up --detach --build librarian
```

The experimental limits are 1 GiB and two CPUs for Qdrant, and 512 MiB and one
CPU for the librarian. Both services publish loopback ports only during local
development. Check health and resource use:

```bash
docker compose ps

curl --fail --silent http://127.0.0.1:8091/health/ready \
  | python3 -m json.tool

docker stats --no-stream \
  qdrant-dev \
  librarian-dev
```

Stop the service without deleting Qdrant data or snapshots:

```bash
docker compose stop librarian
```

Do not add `--volumes` to the stop/down commands unless deleting the complete
local Qdrant catalog is intentional.

The 2026-09-10 container verification produced these measurements:

- 130 MB librarian image, with neither PyTorch nor DuckDB installed.
- Approximately 210-290 MiB librarian memory, including two simultaneous
  end-to-end recommendation requests, under the 512 MiB limit.
- Approximately 500 MiB settled Qdrant memory under the 1 GiB limit.
- 1.73 GiB for the fully indexed runtime collection and 64 MiB for the mounted
  ONNX model cache.
- Two simultaneous requests completed in about 1.76 seconds and returned ten
  total validated recommendations.

Docker Desktop is useful evidence but is not the final Linux/VPS capacity test.

### Package the runtime collection for deployment

The deployment snapshot must come from the enriched runtime collection, not
the earlier evaluation collection. Create it, regenerate the catalog manifest
against that exact collection, and download it into an ignored deployment
directory:

```bash
.data/openlibrary/.venv/bin/python \
  tools/openlibrary-import/qdrant_catalog.py \
  --collection papermast_fiction_bge_runtime_v1 snapshot

.data/openlibrary/.venv/bin/python \
  tools/openlibrary-import/finalize_catalog.py \
  --collection papermast_fiction_bge_runtime_v1

.data/openlibrary/.venv/bin/python \
  tools/openlibrary-import/package_runtime.py
```

`package_runtime.py` streams the snapshot without loading it into memory,
checks its byte count, calculates SHA-256, and writes
`.data/openlibrary/deployment/catalog-v1/deployment-manifest.json` atomically.
It refuses a manifest for the evaluation collection. An existing complete
snapshot is checksummed and reused, so rerunning the command does not download
another 1.86 GB copy.

The 2026-09-11 package contains 676,258 works in a 1,857,358,848-byte snapshot.
An isolated restore produced a green collection with all 676,258 vectors
indexed. The restored collection used approximately 2.0 GB of disk; the
snapshot is needed during restore and for off-server recovery but need not
remain on the VPS after a verified backup exists elsewhere.

### Exercise the ASP.NET boundary locally

In Development, the PaperMast API defaults the private librarian address to
`http://127.0.0.1:8091` and enables the feature. Start the containerized
librarian as shown above, then start the existing API normally:

```bash
dotnet run --project papermast/papermast.csproj
```

Send the browser-facing request to PaperMast rather than directly to Python:

```bash
curl --fail --silent http://127.0.0.1:5050/api/librarian/recommendations \
  --header 'Content-Type: application/json' \
  --data '{"query":"Something funny and weird.","resultCount":5}' \
  | python3 -m json.tool
```

The endpoint requires an authenticated PaperMast session. The first exact query
can consume one Gemini request. Successful results are
cached in Redis for 60 minutes; repeat requests with equivalent capitalization
and whitespace reuse the cached response. The public endpoint permits five
requests per client IP per minute. It returns a generic `503` with a retry hint
when Python startup, concurrency, Qdrant, or retrieval fails and does not expose
the upstream error to the browser. A caught Gemini failure instead returns the
diversified local Qdrant results with generic metadata-based explanations.

The integration defaults are intentionally local-only. Production leaves the
feature disabled until its private Compose service and these settings are
reviewed together:

- `Librarian__Enabled`
- `Librarian__BaseUrl`
- `Librarian__RequestTimeoutSeconds`
- `Librarian__CacheMinutes`
- `Librarian__CatalogVersion`

Run the focused ASP.NET tests without contacting Gemini or Qdrant:

```bash
dotnet test papermast/papermast.slnx --configuration Release
```
