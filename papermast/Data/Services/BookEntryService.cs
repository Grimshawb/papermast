using Microsoft.EntityFrameworkCore;
using papermast.Entities.Constants;
using papermast.Entities.DTO;
using papermast.Entities.Models;

namespace papermast.Data.Services
{
    public interface IBookEntryService
    {
        Task<IReadOnlyList<BookEntryDto>> GetAll(string identityUserID);
        Task<BookEntryDto> Create(string identityUserID, BookEntryRequest request);
        Task<BookEntryDto?> Update(string identityUserID, uint entryID, BookEntryRequest request);
    }

    public class BookEntryService : IBookEntryService
    {
        private readonly AppDbContext _context;

        public BookEntryService(AppDbContext context)
        {
            _context = context;
        }

        public async Task<IReadOnlyList<BookEntryDto>> GetAll(string identityUserID)
        {
            var userID = await GetUserID(identityUserID);
            var entries = await _context.BookEntries
                .AsNoTracking()
                .Where(entry => entry.UserID == userID)
                .OrderByDescending(entry => entry.UpdatedDate)
                .ToListAsync();
            return entries.Select(ToDto).ToList();
        }

        public async Task<BookEntryDto> Create(string identityUserID, BookEntryRequest request)
        {
            Validate(request);
            var userID = await GetUserID(identityUserID);
            var existing = await FindMatchingEntry(userID, request);

            if (existing is not null)
            {
                Apply(existing, request);
                await _context.SaveChangesAsync();
                return ToDto(existing);
            }

            var entry = new BookEntry { UserID = userID };
            Apply(entry, request);
            _context.BookEntries.Add(entry);
            await _context.SaveChangesAsync();
            return ToDto(entry);
        }

        public async Task<BookEntryDto?> Update(string identityUserID, uint entryID, BookEntryRequest request)
        {
            Validate(request);
            var userID = await GetUserID(identityUserID);
            var entry = await _context.BookEntries.FirstOrDefaultAsync(item =>
                item.EntryID == entryID && item.UserID == userID);
            if (entry is null) return null;

            var matchingEntry = await FindMatchingEntry(userID, request);
            var duplicate = matchingEntry is not null && matchingEntry.EntryID != entryID;
            if (duplicate) throw new InvalidOperationException("This book is already in your library.");

            Apply(entry, request);
            await _context.SaveChangesAsync();
            return ToDto(entry);
        }

        private async Task<int> GetUserID(string identityUserID)
        {
            var userID = await _context.AppUsers
                .Where(user => user.IdentityUserId == identityUserID)
                .Select(user => (int?)user.UserID)
                .SingleOrDefaultAsync();
            return userID ?? throw new InvalidOperationException("The authenticated user profile was not found.");
        }

        private static void Validate(BookEntryRequest request)
        {
            if (!BookStatus.IsValid(request.Status))
                throw new ArgumentException("The selected reading status is not valid.");
            if (string.IsNullOrWhiteSpace(request.Isbn10) &&
                string.IsNullOrWhiteSpace(request.Isbn13) &&
                (string.IsNullOrWhiteSpace(request.Source) || string.IsNullOrWhiteSpace(request.SourceBookID)))
                throw new ArgumentException("An ISBN or source identifier is required.");
        }

        private async Task<BookEntry?> FindMatchingEntry(int userID, BookEntryRequest request)
        {
            var isbn10 = NormalizeIdentifier(request.Isbn10);
            var isbn13 = NormalizeIdentifier(request.Isbn13);
            var source = request.Source?.Trim();
            var sourceBookID = request.SourceBookID?.Trim();

            return await _context.BookEntries.FirstOrDefaultAsync(entry =>
                entry.UserID == userID &&
                ((!string.IsNullOrEmpty(isbn13) && entry.Isbn13 == isbn13) ||
                 (!string.IsNullOrEmpty(isbn10) && entry.Isbn10 == isbn10) ||
                 (!string.IsNullOrEmpty(source) && !string.IsNullOrEmpty(sourceBookID) &&
                  entry.Source == source && entry.SourceBookID == sourceBookID)));
        }

        private static void Apply(BookEntry entry, BookEntryRequest request)
        {
            var previousStatus = entry.Status;
            entry.Source = request.Source?.Trim();
            entry.SourceBookID = request.SourceBookID?.Trim();
            entry.Title = request.Title.Trim();
            entry.Authors = request.Authors?.Trim();
            entry.ThumbnailUrl = request.ThumbnailUrl?.Trim();
            entry.Isbn10 = NormalizeIdentifier(request.Isbn10);
            entry.Isbn13 = NormalizeIdentifier(request.Isbn13);
            entry.Status = BookStatus.All.First(status =>
                status.Equals(request.Status, StringComparison.OrdinalIgnoreCase));
            entry.PageCount = request.PageCount;

            if (entry.Status == BookStatus.READING && entry.StartDate is null)
                entry.StartDate = DateTime.UtcNow;
            if (entry.Status == BookStatus.READ && previousStatus != BookStatus.READ)
            {
                entry.EndDate = DateTime.UtcNow;
                entry.PercentCompleted = 100;
                if (entry.PageCount > 0) entry.PagesCompleted = entry.PageCount;
            }

            entry.UpdatedDate = DateTime.UtcNow;
        }

        private static string? NormalizeIdentifier(string? value) =>
            string.IsNullOrWhiteSpace(value)
                ? null
                : value.Replace("-", string.Empty).Replace(" ", string.Empty).ToUpperInvariant();

        private static BookEntryDto ToDto(BookEntry entry) => new()
        {
            EntryID = entry.EntryID,
            Source = entry.Source,
            SourceBookID = entry.SourceBookID,
            Title = entry.Title,
            Authors = entry.Authors,
            ThumbnailUrl = entry.ThumbnailUrl,
            Isbn10 = entry.Isbn10,
            Isbn13 = entry.Isbn13,
            Status = entry.Status ?? BookStatus.TO_BE_READ,
            PageCount = entry.PageCount,
            PagesCompleted = entry.PagesCompleted,
            PercentCompleted = entry.PercentCompleted,
            Rating = entry.Rating,
            StartDate = entry.StartDate,
            EndDate = entry.EndDate,
            CreatedDate = entry.CreatedDate,
            UpdatedDate = entry.UpdatedDate
        };
    }
}
