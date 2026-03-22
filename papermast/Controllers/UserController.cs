
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;
using papermast.Entities.Models;

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

        [HttpDelete("{userID}")]
        public async Task<ActionResult<bool>> DeleteUser([FromRoute] int userID)
        {
            try
            {
                return Ok(this._userService.DeleteUser(userID));
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Deleting User Account: {ex.Message}");
            }
        }
    }
}
