using Microsoft.EntityFrameworkCore;
using papermast.Entities.Constants;
using papermast.Entities.DTO;
using papermast.Entities.Models;

namespace papermast.Data.Services
{
    public interface IReadingGoalService
    {
        Task<ReadingGoalDto> Get(string identityUserID, int year);
        Task<ReadingGoalDto> Upsert(string identityUserID, ReadingGoalRequest request);
    }

    public class ReadingGoalService : IReadingGoalService
    {
        private readonly AppDbContext _context;

        public ReadingGoalService(AppDbContext context)
        {
            _context = context;
        }

        public async Task<ReadingGoalDto> Get(string identityUserID, int year)
        {
            ValidateYear(year);
            var userID = await GetUserID(identityUserID);
            return await BuildDto(userID, year);
        }

        public async Task<ReadingGoalDto> Upsert(string identityUserID, ReadingGoalRequest request)
        {
            ValidateYear(request.Year);
            if (request.TargetBookCount < 1 || request.TargetBookCount > 1000)
                throw new ArgumentException("The reading target must be between 1 and 1,000 books.");

            var userID = await GetUserID(identityUserID);
            var goal = await _context.ReadingGoals.SingleOrDefaultAsync(item =>
                item.UserID == userID && item.Year == request.Year);

            if (goal is null)
            {
                goal = new ReadingGoal { UserID = userID, Year = request.Year };
                _context.ReadingGoals.Add(goal);
            }

            goal.TargetBookCount = request.TargetBookCount;
            goal.UpdatedDate = DateTime.UtcNow;
            await _context.SaveChangesAsync();
            return await BuildDto(userID, request.Year);
        }

        private async Task<ReadingGoalDto> BuildDto(int userID, int year)
        {
            var target = await _context.ReadingGoals
                .AsNoTracking()
                .Where(item => item.UserID == userID && item.Year == year)
                .Select(item => (int?)item.TargetBookCount)
                .SingleOrDefaultAsync() ?? 0;
            var completed = await _context.BookEntries
                .AsNoTracking()
                .CountAsync(entry => entry.UserID == userID &&
                    entry.Status == BookStatus.READ &&
                    entry.EndDate.HasValue &&
                    entry.EndDate.Value.Year == year);

            return new ReadingGoalDto
            {
                Year = year,
                TargetBookCount = target,
                CompletedBookCount = completed
            };
        }

        private async Task<int> GetUserID(string identityUserID)
        {
            var userID = await _context.AppUsers
                .Where(user => user.IdentityUserId == identityUserID)
                .Select(user => (int?)user.UserID)
                .SingleOrDefaultAsync();
            return userID ?? throw new InvalidOperationException("The authenticated user profile was not found.");
        }

        private static void ValidateYear(int year)
        {
            if (year < 2000 || year > DateTime.UtcNow.Year + 1)
                throw new ArgumentException("The selected reading-goal year is not valid.");
        }
    }
}
