using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;
using papermast.Entities.Models;
using System.Security.Claims;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class UserController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IUserService _userService;

        public UserController(UserManager<ApplicationUser> userManager, IUserService userService)
        {
            _userManager = userManager;
            _userService = userService;
        }

        [Authorize(AuthenticationSchemes = "Bearer")]
        [HttpDelete]
        public async Task<ActionResult<bool>> DeleteUser()
        {
            try
            {
                var identityUserID = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
                if (string.IsNullOrEmpty(identityUserID)) return Unauthorized();

                var appUser = await _userService.GetAppUserByIdentityID(identityUserID);
                if (appUser == null) return NotFound();

                return Ok(await _userService.DeleteUser(appUser.UserID));
            }
            catch
            {
                return BadRequest("Unable to delete the user account.");
            }
        }
    }
}
