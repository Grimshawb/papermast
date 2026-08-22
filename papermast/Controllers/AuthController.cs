using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using papermast.Data.Services;
using papermast.Entities.DTO;
using papermast.Entities.Models;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IConfiguration _config;
        private readonly IUserService _userService;
        private readonly ILogger<AuthController> _logger;

        public AuthController(UserManager<ApplicationUser> userManager, IConfiguration config, IUserService userService, ILogger<AuthController> logger)
        {
            _userManager = userManager;
            _config = config;
            _userService = userService;
            _logger = logger;
        }

        [EnableRateLimiting("authentication")]
        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegistrationRequest request)
        {
            try
            {
                return Ok(await _userService.CreateUser(request));
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Registration failed");
                return BadRequest("Unable to register with the supplied information.");
            }
        }

        [EnableRateLimiting("authentication")]
        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginRequest request)
        {
            try
            {
                var user = await _userManager.FindByEmailAsync(request.Email!);
                if (user == null || !await _userManager.CheckPasswordAsync(user, request.Password!))
                    return Unauthorized();

                var token = JwtHelper.GenerateToken(user, _config, await _userManager.GetRolesAsync(user));
                
                Response.Cookies.Append("papermast_auth", token, new CookieOptions
                {
                    HttpOnly = true,
                    Secure = true, 
                    SameSite = SameSiteMode.Lax,
                    Expires = DateTimeOffset.UtcNow.AddHours(24)
                });

                return Ok(true);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Login failed unexpectedly");
                return BadRequest("Unable to complete login.");
            }
        }

        [HttpPost("logout")]
        public IActionResult Logout()
        {
            try
            {
                Response.Cookies.Delete("papermast_auth", new CookieOptions
                {
                    HttpOnly = true,
                    Secure = true, 
                    SameSite = SameSiteMode.Lax
                });
                return Ok();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Logout failed unexpectedly");
                return BadRequest("Unable to complete logout.");
            }
        }

        [EnableRateLimiting("authentication")]
        [HttpGet("email-exists/{email}")]
        public async Task<ActionResult<bool>> EmailExists([FromRoute] string? email)
        {
            try
            {
                return Ok(await _userService.EmailExists(email ?? string.Empty));
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Email availability check failed");
                return BadRequest("Unable to check email availability.");
            }
        }

        [Authorize(AuthenticationSchemes = "Bearer")]
        [HttpGet]
        public async Task<ActionResult<UserDto>> GetLoggedInUser()
        {
            try
            {
                var identityUserID = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

                // Get the appUser by userId
                if (!string.IsNullOrEmpty(identityUserID))
                {
                    var appUser = await this._userService.GetAppUserByIdentityID(identityUserID);
                    if (appUser is not null) appUser.IsAdmin = User.IsInRole("Admin");
                    return Ok(appUser);
                }
                return NotFound("AppUser not found");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to retrieve logged-in user");
                return BadRequest("Unable to retrieve the logged-in user.");
            }
        }
    }
}
