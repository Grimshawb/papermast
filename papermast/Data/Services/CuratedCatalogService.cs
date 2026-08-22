using Microsoft.EntityFrameworkCore;
using papermast.Entities.DTO;
using papermast.Entities.Models;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace papermast.Data.Services;

public interface ICuratedCatalogService
{
    Task<CuratedCatalogResponse> GetPublished(string slug);
    Task<(CatalogImportPreviewDto? Preview, IReadOnlyList<CatalogImportErrorDto> Errors)> Import(string slug, string section, Stream csv, string userId);
    Task<CuratedCatalogResponse?> Publish(string slug, int batchId);
    Task<CuratedCatalogResponse?> SetCoverOverride(string slug, int batchId, string isbn, string? url);
    Task<CatalogImportPreviewDto?> GetPublishedForAdmin(string slug);
    Task<(CuratedCatalogResponse? Catalog, string? Error)> AddBook(string slug, int batchId, string section, string isbn);
    Task<CuratedCatalogResponse?> RemoveBook(string slug, int batchId, string isbn);
}

public class CuratedCatalogService(AppDbContext db, IBooksApiService booksApi, IOpenLibraryService openLibrary) : ICuratedCatalogService
{
    private static readonly string[] Columns = ["isbn", "title", "author"];
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<CuratedCatalogResponse> GetPublished(string slug)
    {
        var batch = await db.CuratedCatalogBatches.AsNoTracking().Include(item => item.Books)
            .Where(item => item.GenreSlug == slug && item.Status == "Published")
            .OrderByDescending(item => item.PublishedAtUtc).FirstOrDefaultAsync();
        return ToResponse(slug, batch);
    }

    public async Task<CatalogImportPreviewDto?> GetPublishedForAdmin(string slug)
    {
        var batch = await db.CuratedCatalogBatches.AsNoTracking().Include(item => item.Books)
            .Where(item => item.GenreSlug == slug && item.Status == "Published")
            .OrderByDescending(item => item.PublishedAtUtc).FirstOrDefaultAsync();
        return batch is null ? null : new(batch.CuratedCatalogBatchID, ToResponse(slug, batch), []);
    }

    public async Task<(CatalogImportPreviewDto? Preview, IReadOnlyList<CatalogImportErrorDto> Errors)> Import(string slug, string section, Stream csv, string userId)
    {
        var errors = new List<CatalogImportErrorDto>();
        List<string[]> records;
        using (var reader = new StreamReader(csv, new UTF8Encoding(false, true), false, leaveOpen: true))
        {
            try { records = ParseCsv(await reader.ReadToEndAsync()); }
            catch (Exception ex) { return (null, [new(1, "file", ex.Message)]); }
        }

        if (records.Count == 0) return (null, [new(1, "file", "The CSV is empty.")]);
        var headers = records[0].Select(value => value.Trim().ToLowerInvariant()).ToArray();
        var unknown = headers.Except(Columns).ToArray();
        var missing = Columns.Except(headers).ToArray();
        var duplicateHeaders = headers.GroupBy(value => value).Where(group => group.Count() > 1).Select(group => group.Key).ToArray();
        if (unknown.Length > 0) errors.Add(new(1, "header", $"Unknown columns: {string.Join(", ", unknown)}."));
        if (missing.Length > 0) errors.Add(new(1, "header", $"Missing columns: {string.Join(", ", missing)}."));
        if (duplicateHeaders.Length > 0) errors.Add(new(1, "header", $"Duplicate columns: {string.Join(", ", duplicateHeaders)}."));
        if (errors.Count > 0) return (null, errors);

        var index = headers.Select((name, i) => (name, i)).ToDictionary(item => item.name, item => item.i);
        var rows = new List<ImportRow>();
        for (var i = 1; i < records.Count; i++)
        {
            var values = records[i];
            if (values.All(string.IsNullOrWhiteSpace)) continue;
            if (values.Length != headers.Length) { errors.Add(new(i + 1, "row", $"Expected {headers.Length} columns but found {values.Length}.")); continue; }
            string Get(string name) => values[index[name]].Trim();
            var rawIsbn = Get("isbn");
            var validIsbn = TryNormalizeIsbn(rawIsbn, out var isbn);
            var title = Get("title"); var author = Get("author");
            var errorCountBeforeRow = errors.Count;
            if (!validIsbn) errors.Add(new(i + 1, "isbn", "Enter a valid ISBN-10 or ISBN-13."));
            if (title.Length == 0) errors.Add(new(i + 1, "title", "Title is required."));
            if (author.Length == 0) errors.Add(new(i + 1, "author", "Author is required."));
            if (errors.Count == errorCountBeforeRow)
                rows.Add(new(i + 1, section, rows.Count + 1, isbn, title, author));
        }
        var seenIsbns = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        rows = rows.Where(row =>
        {
            if (seenIsbns.Add(row.Isbn)) return true;
            errors.Add(new(row.Line, "isbn", "ISBN is duplicated; the first occurrence was kept."));
            return false;
        }).Select((row, position) => row with { Position = position + 1 }).ToList();
        if (rows.Count == 0) errors.Add(new(1, "file", "The CSV contains no books."));
        if (rows.Count == 0) return (null, errors);

        var isbns = rows.Select(row => row.Isbn).ToArray();
        var metadataByIsbn = await db.BookMetadata.Where(item => isbns.Contains(item.Isbn13))
            .ToDictionaryAsync(item => item.Isbn13, StringComparer.OrdinalIgnoreCase);
        var missingIsbns = isbns.Where(isbn => !metadataByIsbn.ContainsKey(isbn)).ToArray();

        if (missingIsbns.Length > 0)
        {
            IReadOnlyDictionary<string, JsonObject> openLibraryBooks = new Dictionary<string, JsonObject>();
            try { openLibraryBooks = await openLibrary.GetBooksByIsbn(missingIsbns); }
            catch { /* Google Books below remains the fallback for the whole unresolved set. */ }
            foreach (var (isbn, book) in openLibraryBooks)
            {
                var metadata = FromOpenLibrary(isbn, book);
                if (metadata is null) continue;
                db.BookMetadata.Add(metadata);
                metadataByIsbn[isbn] = metadata;
            }
        }

        var googleFallback = isbns.Where(isbn => !metadataByIsbn.ContainsKey(isbn)).ToArray();
        foreach (var isbn in googleFallback)
        {
            try
            {
                var json = await booksApi.Search(null, null, null, null, isbn);
                var item = (JsonNode.Parse(json ?? "{}")?["items"] as JsonArray)?.OfType<JsonObject>().FirstOrDefault();
                var metadata = FromGoogle(isbn, item);
                if (metadata is null) continue;
                db.BookMetadata.Add(metadata);
                metadataByIsbn[isbn] = metadata;
            }
            catch { /* Report the unresolved ISBN against its CSV row below. */ }
        }

        // Keep successfully resolved metadata even when another row prevents this catalog from publishing.
        if (db.ChangeTracker.HasChanges()) await db.SaveChangesAsync();

        var batch = new CuratedCatalogBatch { GenreSlug = slug, CreatedByUserID = userId };
        var otherSection = section == "popular" ? "upcoming" : "popular";
        var publishedOtherBooks = await db.CuratedCatalogBatches.AsNoTracking().Where(item => item.GenreSlug == slug && item.Status == "Published")
            .OrderByDescending(item => item.PublishedAtUtc).SelectMany(item => item.Books).Where(book => book.Section == otherSection).ToListAsync();
        var importedIsbns = rows.Select(row => row.Isbn).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var invalidRows = new HashSet<int>();
        foreach (var existing in publishedOtherBooks)
        {
            if (importedIsbns.Contains(existing.Isbn13))
            {
                var row = rows.First(item => item.Isbn.Equals(existing.Isbn13, StringComparison.OrdinalIgnoreCase));
                errors.Add(new(row.Line, "isbn", $"This ISBN is already in the {otherSection} section."));
                invalidRows.Add(row.Line);
                continue;
            }
            batch.Books.Add(Clone(existing));
        }
        foreach (var row in rows)
        {
            if (!metadataByIsbn.TryGetValue(row.Isbn, out var metadata))
            {
                errors.Add(new(row.Line, "isbn13", "No book metadata was found for this ISBN."));
                continue;
            }
            var authors = JsonSerializer.Deserialize<string[]>(metadata.AuthorsJson) ?? [];
            var matches = true;
            if (!Comparable(metadata.Title).Contains(Comparable(row.Title)) && !Comparable(row.Title).Contains(Comparable(metadata.Title)))
            {
                errors.Add(new(row.Line, "title", $"Resolved title '{metadata.Title}' does not match the CSV."));
                matches = false;
            }
            if (!authors.Any(value => Comparable(value).Contains(Comparable(row.Author)) || Comparable(row.Author).Contains(Comparable(value))))
            {
                errors.Add(new(row.Line, "author", $"Resolved authors '{string.Join(", ", authors)}' do not match the CSV."));
                matches = false;
            }
            if (!matches || invalidRows.Contains(row.Line)) continue;
            batch.Books.Add(new CuratedCatalogBook {
                Section = row.Section, Position = row.Position, Isbn13 = row.Isbn,
                SourceBookID = metadata.SourceBookID, Title = metadata.Title, AuthorsJson = metadata.AuthorsJson,
                Description = metadata.Description, CoverUrl = metadata.CoverOverrideUrl ?? metadata.CoverUrl, Publisher = metadata.Publisher,
                IdentifiersJson = metadata.IdentifiersJson, PublishedDate = metadata.PublishedDate,
                ReleaseDate = row.Section == "upcoming" && DateTime.TryParse(metadata.PublishedDate, CultureInfo.InvariantCulture, DateTimeStyles.None, out var releaseDate) ? releaseDate : null
            });
        }
        var importedCount = batch.Books.Count(book => book.Section == section);
        if (importedCount == 0)
        {
            errors.Add(new(1, "file", "No valid rows were available to preview."));
            return (null, errors);
        }
        db.CuratedCatalogBatches.Add(batch);
        await db.SaveChangesAsync();
        return (new(batch.CuratedCatalogBatchID, ToResponse(slug, batch), errors), errors);
    }

    public async Task<CuratedCatalogResponse?> Publish(string slug, int batchId)
    {
        await using var transaction = await db.Database.BeginTransactionAsync();
        var draft = await db.CuratedCatalogBatches.Include(item => item.Books)
            .SingleOrDefaultAsync(item => item.CuratedCatalogBatchID == batchId && item.GenreSlug == slug && (item.Status == "Draft" || item.Status == "Published"));
        if (draft is null) return null;
        var published = await db.CuratedCatalogBatches.Where(item => item.GenreSlug == slug && item.Status == "Published").ToListAsync();
        foreach (var old in published) old.Status = "Archived";
        draft.Status = "Published"; draft.PublishedAtUtc = DateTime.UtcNow;
        await db.SaveChangesAsync(); await transaction.CommitAsync();
        return ToResponse(slug, draft);
    }

    public async Task<CuratedCatalogResponse?> SetCoverOverride(string slug, int batchId, string isbn, string? url)
    {
        if (!TryNormalizeIsbn(isbn, out var isbn13)) return null;
        var batch = await db.CuratedCatalogBatches.Include(item => item.Books)
            .SingleOrDefaultAsync(item => item.CuratedCatalogBatchID == batchId && item.GenreSlug == slug && item.Status == "Draft");
        var draftBook = batch?.Books.SingleOrDefault(book => book.Isbn13 == isbn13);
        var metadata = await db.BookMetadata.SingleOrDefaultAsync(item => item.Isbn13 == isbn13);
        if (batch is null || draftBook is null || metadata is null) return null;
        metadata.CoverOverrideUrl = string.IsNullOrWhiteSpace(url) ? null : url;
        draftBook.CoverUrl = metadata.CoverOverrideUrl ?? metadata.CoverUrl;
        await db.SaveChangesAsync();
        return ToResponse(slug, batch);
    }

    public async Task<(CuratedCatalogResponse? Catalog, string? Error)> AddBook(string slug, int batchId, string section, string isbn)
    {
        if (!TryNormalizeIsbn(isbn, out var isbn13)) return (null, "Enter a valid ISBN-10 or ISBN-13.");
        var batch = await db.CuratedCatalogBatches.Include(item => item.Books)
            .SingleOrDefaultAsync(item => item.CuratedCatalogBatchID == batchId && item.GenreSlug == slug && item.Status == "Draft");
        if (batch is null) return (null, "Draft catalog not found.");
        if (batch.Books.Any(book => book.Isbn13 == isbn13)) return (null, "This ISBN is already in the draft.");

        var metadata = await ResolveMetadata(isbn13);
        if (metadata is null) return (null, "No book metadata was found for this ISBN.");
        batch.Books.Add(new CuratedCatalogBook
        {
            Section = section,
            Position = batch.Books.Where(book => book.Section == section).Select(book => book.Position).DefaultIfEmpty().Max() + 1,
            Isbn13 = isbn13, SourceBookID = metadata.SourceBookID, Title = metadata.Title, AuthorsJson = metadata.AuthorsJson,
            Description = metadata.Description, CoverUrl = metadata.CoverOverrideUrl ?? metadata.CoverUrl,
            Publisher = metadata.Publisher, IdentifiersJson = metadata.IdentifiersJson, PublishedDate = metadata.PublishedDate,
            ReleaseDate = section == "upcoming" && DateTime.TryParse(metadata.PublishedDate, CultureInfo.InvariantCulture, DateTimeStyles.None, out var date) ? date : null
        });
        await db.SaveChangesAsync();
        return (ToResponse(slug, batch), null);
    }

    public async Task<CuratedCatalogResponse?> RemoveBook(string slug, int batchId, string isbn)
    {
        if (!TryNormalizeIsbn(isbn, out var isbn13)) return null;
        var batch = await db.CuratedCatalogBatches.Include(item => item.Books)
            .SingleOrDefaultAsync(item => item.CuratedCatalogBatchID == batchId && item.GenreSlug == slug && item.Status == "Draft");
        var book = batch?.Books.SingleOrDefault(item => item.Isbn13 == isbn13);
        if (batch is null || book is null) return null;
        var section = book.Section;
        db.CuratedCatalogBooks.Remove(book);
        var remaining = batch.Books.Where(item => item != book && item.Section == section).OrderBy(item => item.Position).ToArray();
        for (var i = 0; i < remaining.Length; i++) remaining[i].Position = i + 1;
        await db.SaveChangesAsync();
        batch.Books.Remove(book);
        return ToResponse(slug, batch);
    }

    private async Task<BookMetadata?> ResolveMetadata(string isbn13)
    {
        var metadata = await db.BookMetadata.SingleOrDefaultAsync(item => item.Isbn13 == isbn13);
        if (metadata is not null) return metadata;
        try
        {
            var books = await openLibrary.GetBooksByIsbn([isbn13]);
            if (books.TryGetValue(isbn13, out var book)) metadata = FromOpenLibrary(isbn13, book);
        }
        catch { /* Google remains the fallback. */ }
        if (metadata is null)
        {
            try
            {
                var json = await booksApi.Search(null, null, null, null, isbn13);
                var item = (JsonNode.Parse(json ?? "{}")?["items"] as JsonArray)?.OfType<JsonObject>().FirstOrDefault();
                metadata = FromGoogle(isbn13, item);
            }
            catch { return null; }
        }
        if (metadata is null) return null;
        db.BookMetadata.Add(metadata);
        await db.SaveChangesAsync();
        return metadata;
    }

    private static CuratedCatalogResponse ToResponse(string slug, CuratedCatalogBatch? batch)
    {
        var books = batch?.Books ?? [];
        CuratedCatalogSectionDto Section(string key, string title) => new(key, title, books.Where(book => book.Section == key)
            .OrderBy(book => book.Position).Select(book => new CuratedCatalogBookDto(book.SourceBookID, book.Title,
                JsonSerializer.Deserialize<string[]>(book.AuthorsJson) ?? [], book.Description, new(book.CoverUrl, book.CoverUrl), book.Publisher,
                JsonSerializer.Deserialize<CuratedIdentifierDto[]>(book.IdentifiersJson) ?? [], book.PublishedDate,
                book.Isbn13, book.ReleaseDate, book.Position)).ToArray());
        return new(slug, batch?.PublishedAtUtc, [Section("popular", "Popular & Recommended"), Section("upcoming", "Coming Soon")]);
    }

    private static bool TryNormalizeIsbn(string value, out string isbn13)
    {
        var normalized = value.Replace("-", "").Replace(" ", "").ToUpperInvariant();
        if (ValidIsbn13(normalized)) { isbn13 = normalized; return true; }
        if (ValidIsbn10(normalized))
        {
            var firstTwelve = $"978{normalized[..9]}";
            var sum = firstTwelve.Select((ch, i) => (ch - '0') * (i % 2 == 0 ? 1 : 3)).Sum();
            isbn13 = $"{firstTwelve}{(10 - sum % 10) % 10}";
            return true;
        }
        isbn13 = normalized;
        return false;
    }

    private static bool ValidIsbn13(string value) => value.Length == 13 && value.All(char.IsDigit)
        && value.Select((ch, i) => (ch - '0') * (i % 2 == 0 ? 1 : 3)).Sum() % 10 == 0;

    private static bool ValidIsbn10(string value)
    {
        if (value.Length != 10 || value[..9].Any(ch => !char.IsDigit(ch)) || (!char.IsDigit(value[9]) && value[9] != 'X')) return false;
        var sum = value[..9].Select((ch, i) => (ch - '0') * (10 - i)).Sum();
        sum += value[9] == 'X' ? 10 : value[9] - '0';
        return sum % 11 == 0;
    }
    private static string Comparable(string value) => new(value.ToLowerInvariant().Where(char.IsLetterOrDigit).ToArray());

    private static CuratedCatalogBook Clone(CuratedCatalogBook book) => new()
    {
        Section = book.Section, Position = book.Position, Isbn13 = book.Isbn13, SourceBookID = book.SourceBookID,
        Title = book.Title, AuthorsJson = book.AuthorsJson, Description = book.Description, CoverUrl = book.CoverUrl,
        Publisher = book.Publisher, IdentifiersJson = book.IdentifiersJson, PublishedDate = book.PublishedDate,
        ReleaseDate = book.ReleaseDate
    };

    private static BookMetadata? FromGoogle(string isbn, JsonObject? item)
    {
        if (item?["volumeInfo"] is not JsonObject volume) return null;
        var title = volume["title"]?.GetValue<string>() ?? "";
        var authors = (volume["authors"] as JsonArray)?.Select(node => node?.GetValue<string>() ?? "")
            .Where(value => value.Length > 0).ToArray() ?? [];
        if (title.Length == 0 || authors.Length == 0) return null;
        var identifiers = (volume["industryIdentifiers"] as JsonArray)?.Deserialize<CuratedIdentifierDto[]>(JsonOptions) ?? [];
        return new BookMetadata {
            Isbn13 = isbn, SourceBookID = item["id"]?.GetValue<string>() ?? $"isbn-{isbn}", Title = title,
            AuthorsJson = JsonSerializer.Serialize(authors), Description = volume["description"]?.GetValue<string>() ?? "",
            CoverUrl = volume["imageLinks"]?["thumbnail"]?.GetValue<string>() ?? volume["imageLinks"]?["smallThumbnail"]?.GetValue<string>() ?? "",
            Publisher = volume["publisher"]?.GetValue<string>() ?? "", IdentifiersJson = JsonSerializer.Serialize(identifiers),
            PublishedDate = volume["publishedDate"]?.GetValue<string>(), Provider = "GoogleBooks"
        };
    }

    private static BookMetadata? FromOpenLibrary(string isbn, JsonObject book)
    {
        var title = book["title"]?.GetValue<string>() ?? "";
        var authors = (book["authors"] as JsonArray)?.OfType<JsonObject>()
            .Select(author => author["name"]?.GetValue<string>() ?? "").Where(value => value.Length > 0).ToArray() ?? [];
        if (title.Length == 0 || authors.Length == 0) return null;
        var publisher = (book["publishers"] as JsonArray)?.OfType<JsonObject>().FirstOrDefault()?["name"]?.GetValue<string>() ?? "";
        var cover = book["cover"]?["large"]?.GetValue<string>() ?? book["cover"]?["medium"]?.GetValue<string>() ?? "";
        var identifiers = new List<CuratedIdentifierDto>();
        if (book["identifiers"] is JsonObject sourceIdentifiers)
        {
            foreach (var (key, type) in new[] { ("isbn_10", "ISBN_10"), ("isbn_13", "ISBN_13") })
                if (sourceIdentifiers[key] is JsonArray values)
                    identifiers.AddRange(values.Select(value => value?.GetValue<string>()).Where(value => !string.IsNullOrWhiteSpace(value))
                        .Select(value => new CuratedIdentifierDto(type, value!)));
        }
        if (!identifiers.Any(value => value.Type == "ISBN_13" && value.Identifier == isbn))
            identifiers.Add(new("ISBN_13", isbn));
        var keyValue = book["key"]?.GetValue<string>() ?? $"isbn-{isbn}";
        return new BookMetadata {
            Isbn13 = isbn, SourceBookID = $"openlibrary-{keyValue.Trim('/').Replace('/', '-')}", Title = title,
            AuthorsJson = JsonSerializer.Serialize(authors), Description = "", CoverUrl = cover, Publisher = publisher,
            IdentifiersJson = JsonSerializer.Serialize(identifiers), PublishedDate = book["publish_date"]?.GetValue<string>(),
            Provider = "OpenLibrary"
        };
    }
    private static List<string[]> ParseCsv(string text)
    {
        var records = new List<string[]>(); var record = new List<string>(); var field = new StringBuilder(); var quoted = false;
        for (var i = 0; i < text.Length; i++)
        {
            var ch = text[i];
            if (quoted && ch == '"' && i + 1 < text.Length && text[i + 1] == '"') { field.Append('"'); i++; }
            else if (ch == '"') quoted = !quoted;
            else if (!quoted && ch == ',') { record.Add(field.ToString()); field.Clear(); }
            else if (!quoted && (ch == '\n' || ch == '\r')) { if (ch == '\r' && i + 1 < text.Length && text[i + 1] == '\n') i++; record.Add(field.ToString()); field.Clear(); records.Add(record.ToArray()); record = []; }
            else field.Append(ch);
        }
        if (quoted) throw new FormatException("The CSV contains an unclosed quoted field.");
        if (field.Length > 0 || record.Count > 0) { record.Add(field.ToString()); records.Add(record.ToArray()); }
        if (records.Count > 0 && records[0].Length > 0) records[0][0] = records[0][0].TrimStart('\uFEFF');
        return records;
    }
    private record ImportRow(int Line, string Section, int Position, string Isbn, string Title, string Author);
}
