using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;
using papermast.Entities.Models;
using System.IdentityModel.Tokens.Jwt;

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
                if (string.IsNullOrEmpty(request?.Email) || string.IsNullOrEmpty(request?.Password)) return BadRequest("Email And Password Are Required To Log In");
                return Ok(await _userService.CreateUser(request));
            }
            catch (Exception ex)
            {
                return BadRequest("Error Registering New User");
            }
        }

        //[HttpPost("login")]
        //public async Task<IActionResult> Login([FromBody] RegistrationRequest request)
        //{
        //    if (string.IsNullOrEmpty(request?.email) || string.IsNullOrEmpty(request?.password)) return BadRequest("Email And Password Are Required To Register");
        //    var user = await _userManager.FindByEmailAsync(request.email);
        //    if (user == null || !await _userManager.CheckPasswordAsync(user, request.password))
        //        return Unauthorized();

        //    var token = JwtHelper.GenerateToken(user, _config);
        //    return Ok(new { token });
        //}
    }
}
