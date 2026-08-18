using Microsoft.AspNetCore.WebUtilities;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace papermast.Data.Services
{

    public interface IBooksApiService
    {
        public Task<string?> DailyAuthorSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn);
        public Task<string?> GenreSearch(string genreSlug);
        public Task<string?> Search(string? text, string? intitle, string? inauthor, string? subject, string? isbn);
    }

    public class BooksApiService: IBooksApiService
    {
        private static readonly IReadOnlyDictionary<string, string[]> GenreSubjects =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                ["fantasy"] = ["fantasy"],
                ["science-fiction"] = ["science fiction"],
                ["mystery"] = ["mystery"],
                ["thriller"] = ["thriller"],
                ["horror"] = ["horror"],
                ["romance"] = ["romance"],
                ["historical-fiction"] = ["historical fiction"],
                ["literary-fiction"] = ["literary fiction"],
                ["biography-memoir"] = ["biography", "memoir"],
                ["history"] = ["history"],
                ["young-adult"] = ["young adult fiction"]
            };

        private readonly IConfiguration _config;
        private readonly IRedisCacheService _cache;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly INytService _nytService;
        private readonly IOpenLibraryService _openLibraryService;

        public BooksApiService(IConfiguration config, IRedisCacheService cache, IHttpClientFactory httpClientFactory,
                               INytService nytService, IOpenLibraryService openLibraryService)
        {
            _config = config;
            _cache = cache;
            _httpClientFactory = httpClientFactory;
            _nytService = nytService;
            _openLibraryService = openLibraryService;
        }

        public async Task<string?> DailyAuthorSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            if (!string.IsNullOrEmpty(inauthor))
            {
                return await _cache.GetOrCreateAsoluteTTLAsync<string?>($"Daily:{inauthor!}", 
                    async () => await apiSearch(text!, intitle!, inauthor!, subject!, isbn!), 
                    TimeSpan.FromDays(1));
            }
            return string.Empty;
        }

        public async Task<string?> Search(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            return await apiSearch(text, intitle, inauthor, subject, isbn);
        }

        public async Task<string?> GenreSearch(string genreSlug)
        {
            if (!GenreSubjects.TryGetValue(genreSlug, out var subjects)) return null;

            var cacheVersion = genreSlug.Equals("horror", StringComparison.OrdinalIgnoreCase) ? "v3" : "v2";
            return await _cache.GetOrCreateAsoluteTTLAsync<string?>(
                $"Genre:{cacheVersion}:{genreSlug.ToLowerInvariant()}",
                async () =>
                {
                    if (genreSlug.Equals("horror", StringComparison.OrdinalIgnoreCase))
                    {
                        var openLibraryTask = _openLibraryService.GetPopularBySubject("horror fiction");
                        var horrorNytTask = _nytService.GetAllBestSellerLists();
                        await Task.WhenAll(openLibraryTask, horrorNytTask);
                        return MergeGenreResults(
                            OpenLibraryToGoogleResults(openLibraryTask.Result),
                            horrorNytTask.Result,
                            genreSlug);
                    }

                    var googleTasks = subjects
                        .Select(subject => apiSearch(null, null, null, subject, null))
                        .ToArray();
                    var nytTask = _nytService.GetAllBestSellerLists();
                    await Task.WhenAll(googleTasks.Cast<Task>().Append(nytTask));
                    return MergeGenreResults(CombineGoogleResults(googleTasks.Select(task => task.Result)), nytTask.Result, genreSlug);
                },
                TimeSpan.FromHours(24));
        }

        private static string OpenLibraryToGoogleResults(string? response)
        {
            var items = new JsonArray();
            if (JsonNode.Parse(response ?? "{}")?["docs"] is not JsonArray works)
                return new JsonObject { ["items"] = items }.ToJsonString();

            foreach (var work in works.OfType<JsonObject>())
            {
                var title = work["title"]?.GetValue<string>();
                var key = work["key"]?.GetValue<string>();
                if (string.IsNullOrWhiteSpace(title) || string.IsNullOrWhiteSpace(key)) continue;

                var identifiers = new JsonArray();
                var isbns = (work["isbn"] as JsonArray)?
                    .Select(node => node?.GetValue<string>())
                    .Where(isbn => !string.IsNullOrWhiteSpace(isbn))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToArray() ?? [];
                var isbn10 = isbns.FirstOrDefault(isbn => isbn!.Length == 10);
                var isbn13 = isbns.FirstOrDefault(isbn => isbn!.Length == 13);
                if (isbn10 is not null) identifiers.Add(new JsonObject { ["type"] = "ISBN_10", ["identifier"] = isbn10 });
                if (isbn13 is not null) identifiers.Add(new JsonObject { ["type"] = "ISBN_13", ["identifier"] = isbn13 });

                var authors = new JsonArray((work["author_name"] as JsonArray)?
                    .Select(author => (JsonNode?)author?.GetValue<string>())
                    .ToArray() ?? []);
                var volumeInfo = new JsonObject
                {
                    ["title"] = title,
                    ["authors"] = authors,
                    ["language"] = "en",
                    ["industryIdentifiers"] = identifiers
                };
                if (work["first_publish_year"] is JsonNode year)
                    volumeInfo["publishedDate"] = year.GetValue<int>().ToString();
                if (work["cover_i"] is JsonNode cover)
                {
                    var coverUrl = $"https://covers.openlibrary.org/b/id/{cover.GetValue<int>()}-L.jpg";
                    volumeInfo["imageLinks"] = new JsonObject { ["smallThumbnail"] = coverUrl, ["thumbnail"] = coverUrl };
                }

                items.Add(new JsonObject
                {
                    ["id"] = $"openlibrary-{key.Trim('/').Replace('/', '-')}",
                    ["volumeInfo"] = volumeInfo,
                    ["papermastSource"] = "open-library"
                });
            }

            return new JsonObject { ["items"] = items }.ToJsonString();
        }

        private static string CombineGoogleResults(IEnumerable<string?> responses)
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var items = new JsonArray();

            foreach (var response in responses)
            {
                if (JsonNode.Parse(response ?? "{}")?["items"] is not JsonArray responseItems) continue;
                foreach (var node in responseItems.OfType<JsonObject>())
                {
                    var clone = node.DeepClone().AsObject();
                    if (seen.Add(Identity(clone))) items.Add(clone);
                }
            }

            return new JsonObject { ["items"] = items }.ToJsonString();
        }

        private static string MergeGenreResults(string? googleJson, string? nytJson, string genreSlug)
        {
            var googleRoot = JsonNode.Parse(googleJson ?? "{}") as JsonObject ?? new JsonObject();
            var googleItems = googleRoot["items"] as JsonArray ?? [];
            var genreIsbns = googleItems
                .SelectMany(item => Identifiers(item?["volumeInfo"]?["industryIdentifiers"] as JsonArray))
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            var merged = new List<(JsonObject Item, bool IsNyt, bool HasCover)>();
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (JsonNode.Parse(nytJson ?? "{}")?["results"]?["lists"] is JsonArray lists)
            {
                var nytBooks = lists
                    .SelectMany(list => list?["books"] as JsonArray ?? [])
                    .OfType<JsonObject>()
                    .ToArray();
                var matchingAuthors = nytBooks
                    .Where(book => FitsGenre(book, genreSlug, genreIsbns))
                    .Select(AuthorIdentity)
                    .Where(author => !string.IsNullOrWhiteSpace(author))
                    .ToHashSet(StringComparer.OrdinalIgnoreCase);

                foreach (var nytBook in nytBooks)
                {
                    if (!FitsGenre(nytBook, genreSlug, genreIsbns) &&
                        !matchingAuthors.Contains(AuthorIdentity(nytBook))) continue;
                    var item = NytToGoogleItem(nytBook);
                    var identity = Identity(item);
                    if (seen.Add(identity)) merged.Add((item, true, HasCover(item)));
                }
            }

            foreach (var node in googleItems)
            {
                if (node is not JsonObject item) continue;
                var clone = item.DeepClone().AsObject();
                var identity = Identity(clone);
                if (seen.Add(identity)) merged.Add((clone, false, HasCover(clone)));
            }

            var items = new JsonArray(merged
                .OrderByDescending(entry => entry.HasCover)
                .ThenByDescending(entry => entry.IsNyt)
                .Select(entry => (JsonNode)entry.Item)
                .ToArray());

            return new JsonObject
            {
                ["kind"] = "books#volumes",
                ["totalItems"] = items.Count,
                ["items"] = items
            }.ToJsonString();
        }

        private static bool FitsGenre(JsonObject book, string genreSlug, HashSet<string> genreIsbns)
        {
            if (Identifiers(book).Any(genreIsbns.Contains)) return true;
            var text = $"{book["title"]} {book["description"]}";
            var pattern = genreSlug.ToLowerInvariant() switch
            {
                "horror" => @"\b(horror|haunted|haunting|ghosts?|vampires?|demons?|demonic|occult|possess(?:ed|ion)|supernatural|gothic|undead)\b",
                "fantasy" => @"\b(fantasy|litrpg|dungeons?|dragons?|magic|magical|mages?|wizards?|witches?|sorcer(?:er|ess|y)|fae|fairy|fairies|elves?|kingdoms?|quests?|enchanted|mythic(?:al)?|gods?|goddesses?)\b",
                "science-fiction" => @"\b(science fiction|sci-fi|space(?:ship|craft)?|aliens?|galactic|dystopi(?:a|an)|time travel|androids?|robots?|extraterrestrial|futuristic)\b",
                "mystery" => @"\b(mystery|mysteries|detectives?|whodunit|murder investigation|investigates?|disappearance|missing person|unsolved)\b",
                "thriller" => @"\b(thriller|conspirac(?:y|ies)|assassins?|espionage|spies?|kidnapped|hostages?|serial killer|race against time)\b",
                "romance" => @"\b(romance|romantic|love story|falls? in love|lovers?|soulmates?|wedding|marriage of convenience)\b",
                "historical-fiction" => @"\b(historical fiction|world war|civil war|victorian|regency|renaissance|medieval|nineteenth century|eighteenth century)\b",
                "literary-fiction" => @"\b(literary fiction|family saga|intergenerational|coming to terms|examines? (?:grief|identity|family)|portrait of a family)\b",
                "biography-memoir" => @"\b(biograph(?:y|ical)|memoirs?|autobiograph(?:y|ical)|life of|personal history|recounts? (?:her|his|their) life)\b",
                "history" => @"\b(history of|historical account|civilization|ancient world|world war|civil war|empire|revolution|presidency|twentieth century)\b",
                "young-adult" => @"\b(young adult|teenagers?|high school|coming[- ]of[- ]age|sixteen-year-old|seventeen-year-old|eighteen-year-old)\b",
                _ => null
            };

            return pattern is not null && Regex.IsMatch(text, pattern,
                RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        }

        private static JsonObject NytToGoogleItem(JsonObject book)
        {
            var isbn10 = book["primary_isbn10"]?.GetValue<string>() ?? string.Empty;
            var isbn13 = book["primary_isbn13"]?.GetValue<string>() ?? string.Empty;
            var image = book["book_image"]?.GetValue<string>() ?? string.Empty;
            var identifiers = new JsonArray();
            if (!string.IsNullOrWhiteSpace(isbn10)) identifiers.Add(new JsonObject { ["type"] = "ISBN_10", ["identifier"] = isbn10 });
            if (!string.IsNullOrWhiteSpace(isbn13)) identifiers.Add(new JsonObject { ["type"] = "ISBN_13", ["identifier"] = isbn13 });

            var volumeInfo = new JsonObject
            {
                ["title"] = book["title"]?.GetValue<string>() ?? "Untitled",
                ["authors"] = new JsonArray(book["author"]?.GetValue<string>() ?? "Unknown author"),
                ["description"] = book["description"]?.GetValue<string>() ?? string.Empty,
                ["publisher"] = book["publisher"]?.GetValue<string>() ?? string.Empty,
                ["language"] = "en",
                ["industryIdentifiers"] = identifiers
            };
            if (!string.IsNullOrWhiteSpace(image))
            {
                volumeInfo["imageLinks"] = new JsonObject { ["smallThumbnail"] = image, ["thumbnail"] = image };
            }

            return new JsonObject
            {
                ["id"] = $"nyt-{isbn13}-{isbn10}".TrimEnd('-'),
                ["volumeInfo"] = volumeInfo,
                ["papermastSource"] = "nyt-bestsellers"
            };
        }

        private static IEnumerable<string> Identifiers(JsonArray? identifiers)
        {
            if (identifiers is null) yield break;
            foreach (var identifier in identifiers)
            {
                var value = identifier?["identifier"]?.GetValue<string>();
                if (!string.IsNullOrWhiteSpace(value)) yield return NormalizeIsbn(value);
            }
        }

        private static IEnumerable<string> Identifiers(JsonObject book)
        {
            foreach (var field in new[] { "primary_isbn10", "primary_isbn13" })
            {
                var value = book[field]?.GetValue<string>();
                if (!string.IsNullOrWhiteSpace(value)) yield return NormalizeIsbn(value);
            }
        }

        private static string Identity(JsonObject item)
        {
            var identifiers = Identifiers(item["volumeInfo"]?["industryIdentifiers"] as JsonArray).ToArray();
            if (identifiers.Length > 0) return identifiers[0];
            return $"{item["volumeInfo"]?["title"]}|{item["volumeInfo"]?["authors"]?[0]}";
        }

        private static bool HasCover(JsonObject item) =>
            !string.IsNullOrWhiteSpace(item["volumeInfo"]?["imageLinks"]?["thumbnail"]?.GetValue<string>());

        private static string NormalizeIsbn(string isbn) =>
            isbn.Replace("-", string.Empty).Replace(" ", string.Empty);

        private static string AuthorIdentity(JsonObject book) =>
            (book["author"]?.GetValue<string>() ?? string.Empty).Trim();

        private async Task<string?> apiSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            var apiKey = _config["GoogleBooks:ApiKey"]
                ?? throw new InvalidOperationException("GoogleBooks:ApiKey is required.");
            var apiUrl = _config["GoogleBooks:ApiUrl"]
                ?? throw new InvalidOperationException("GoogleBooks:ApiUrl is required.");
            var queryParts = new List<string>();

            if (!string.IsNullOrEmpty(text)) queryParts.Add(text);
            if (!string.IsNullOrEmpty(intitle)) queryParts.Add(BuildFieldQuery("intitle", intitle));
            if (!string.IsNullOrEmpty(inauthor)) queryParts.Add(BuildFieldQuery("inauthor", inauthor));
            if (!string.IsNullOrEmpty(subject)) queryParts.Add(BuildFieldQuery("subject", subject));
            if (!string.IsNullOrEmpty(isbn))
                queryParts.Add($"isbn:{isbn.Replace("-", string.Empty).Replace(" ", string.Empty)}");

            var query = queryParts.Count > 0 ? string.Join(" ", queryParts) : "";
            if (string.IsNullOrEmpty(query)) throw new Exception("Cannot Search With Empty Query");

            var queryParams = new Dictionary<string, string?>
            {
                ["q"] = query,
                ["orderBy"] = "relevance",
                ["startIndex"] = "0",
                ["maxResults"] = "40",
                ["key"] = apiKey,
            };
            var url = QueryHelpers.AddQueryString(apiUrl, queryParams);
            var client = _httpClientFactory.CreateClient();
            var response = await client.GetAsync(url);
            //var response = await client.GetAsync($"{apiUrl}{query}&key={apiKey}");
            if (!response.IsSuccessStatusCode) throw new Exception($"Error Searching For Books: {response.StatusCode}");

            return await response.Content.ReadAsStringAsync();
        }

        private static string BuildFieldQuery(string field, string value)
        {
            var terms = value.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            return string.Join(" ", terms.Select(term => $"{field}:{term}"));
        }
    }
}
