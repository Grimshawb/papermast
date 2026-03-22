using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using papermast.Entities.DTO;
using papermast.Entities.Models;

namespace papermast.Data.Services
{
    public interface IUserService
    {
        public Task<bool> CreateUser(RegistrationRequest request);
        public Task<bool> DeleteUser(int userID);
        public Task<UserDto?> GetAppUserByIdentityID(string identityUserID);
        public Task<bool> EmailExists(string email);
    }

    public class UserService : IUserService
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly AppDbContext _context;

        public UserService(UserManager<ApplicationUser> userManager, AppDbContext context)
        {
            _userManager = userManager;
            _context = context;
        }

        public async Task<bool> CreateUser(RegistrationRequest request)
        {
            var identityUser = new ApplicationUser
            {
                UserName = request.Username,
                Email = request.Email
            };

            var result = await _userManager.CreateAsync(identityUser, request.Password);
            if (!result.Succeeded) throw new Exception("Error Creating User Identity");

            // Create the AppUser linked to Identity
            var appUser = new AppUser
            {
                IdentityUserId = identityUser.Id,
                FirstName = request.FirstName,
                LastName = request.LastName
            };

            _context.AppUsers.Add(appUser);
            await _context.SaveChangesAsync();

            return true;
        }

        public async Task<bool> DeleteUser(int userID)
        {
            var appUser = await _context.AppUsers.FirstOrDefaultAsync(u => u.UserID == userID);
            if (appUser != null)
            {
                var identityUser = await _userManager.FindByIdAsync(appUser.IdentityUserId);
                if (identityUser != null)
                {
                    using var tx = await _context.Database.BeginTransactionAsync();
                    try
                    {
                        var userEntries = _context.BookEntries.Where(e => e.UserID == userID);
                        if (userEntries.Any()) _context.BookEntries.RemoveRange(userEntries);
                        _context.AppUsers.Remove(appUser);
                        var result = await _userManager.DeleteAsync(identityUser);

                        if (!result.Succeeded)
                        {
                            await tx.RollbackAsync();
                            return false;
                        }

                        await _context.SaveChangesAsync();
                        await tx.CommitAsync();
                    }
                    catch
                    {
                        await tx.RollbackAsync();
                        throw;
                    }
                }
            }
            return true;
        }

        public async Task<UserDto?> GetAppUserByIdentityID(string identityUserID)
        {
            var user = await _context.AppUsers.Include(a => a.IdentityUser).FirstOrDefaultAsync(a => a.IdentityUserId == identityUserID);
            if (user == null) return null;
            return new UserDto
            {
                UserID = user.UserID,
                Email = user.IdentityUser.Email,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Username = user.Username
            };
        }

        public async Task<bool> EmailExists(string email)
        {
            if (string.IsNullOrEmpty(email)) return true;
            return await _context.Users.AnyAsync(u => u.Email.ToLower() == email.ToLower());
        }
    }
}
