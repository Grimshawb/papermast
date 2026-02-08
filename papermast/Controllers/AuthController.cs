using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.IdentityModel.Tokens.Jwt;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly UserManager<IdentityUser> _userManager;
        private readonly IConfiguration _config;

        public AuthController(UserManager<IdentityUser> userManager, IConfiguration config)
        {
            _userManager = userManager;
            _config = config;
        }

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegistrationRequest request)
        {
            if (string.IsNullOrEmpty(request?.email) || string.IsNullOrEmpty(request?.password)) return BadRequest("Email And Password Are Required To Log In");
            var user = new IdentityUser { UserName = request.email, Email = request.email };
            var result = await _userManager.CreateAsync(user, request.password);

            if (!result.Succeeded)
                return BadRequest(result.Errors);

            return Ok();
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] RegistrationRequest request)
        {
            if (string.IsNullOrEmpty(request?.email) || string.IsNullOrEmpty(request?.password)) return BadRequest("Email And Password Are Required To Register");
            var user = await _userManager.FindByEmailAsync(request.email);
            if (user == null || !await _userManager.CheckPasswordAsync(user, request.password))
                return Unauthorized();

            var token = JwtHelper.GenerateToken(user, _config);
            return Ok(new { token });
        }
    }
}
