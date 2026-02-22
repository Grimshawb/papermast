using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using papermast.Entities.DTO;
using papermast.Entities.Models;

namespace papermast.Data.Services
{
    public interface IUserService
    {
        public Task<bool> CreateUser(RegistrationRequest request);
        public Task<UserDto?> GetAppUserByIdentityID(string identityUserID);
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
    }
}
