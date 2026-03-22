using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
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

        public AuthController(UserManager<ApplicationUser> userManager, IConfiguration config, IUserService userService)
        {
            _userManager = userManager;
            _config = config;
            _userService = userService;
        }

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegistrationRequest request)
        {
            try
            {
                if (string.IsNullOrEmpty(request?.Email) || string.IsNullOrEmpty(request?.Password)) return BadRequest("Email And Password Are Required To Register");
                return Ok(await _userService.CreateUser(request));
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Registering New User: {ex.Message}");
            }
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginRequest request)
        {
            try
            {
                if (string.IsNullOrEmpty(request?.Email) || string.IsNullOrEmpty(request?.Password)) return BadRequest("Email And Password Are Required To Log In");
                var user = await _userManager.FindByEmailAsync(request.Email);
                if (user == null || !await _userManager.CheckPasswordAsync(user, request.Password))
                    return Unauthorized();

                var token = JwtHelper.GenerateToken(user, _config);
                
                Response.Cookies.Append("papermast_auth", token, new CookieOptions
                {
                    HttpOnly = true,
                    Secure = true, 
                    SameSite = SameSiteMode.None, 
                    Expires = DateTimeOffset.UtcNow.AddDays(7)
                });

                return Ok(true);
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Logging In User: {ex.Message}");
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
                    SameSite = SameSiteMode.None 
                });
                return Ok();
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Logging Out: {ex.Message}");
            }
        }

        [HttpGet("email-exists/{email}")]
        public async Task<ActionResult<bool>> EmailExists([FromRoute] string? email)
        {
            try
            {
                return Ok(this._userService.EmailExists(email));
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Validating Email: {ex.Message}");
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
                    return Ok(appUser);
                }
                return NotFound("AppUser not found");
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Retrieving Logged In User: {ex.Message}");
            }
        }
    }
}
