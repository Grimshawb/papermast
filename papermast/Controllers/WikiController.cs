using papermast.Data.Services;
using papermast.Entities.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.IdentityModel.Tokens.Jwt;
using System.Net.Http;
using static System.Net.WebRequestMethods;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class WikiController : ControllerBase
    {
        private readonly IWikiService _wikiService;
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IConfiguration _config;
        private readonly IUserService _userService;

        public WikiController(UserManager<ApplicationUser> userManager, IConfiguration config, IUserService userService, 
                              IWikiService wikiService)
        {
            _userManager = userManager;
            _config = config;
            _userService = userService;
            _wikiService = wikiService;
        }


        [HttpGet("{author}")]
        public async Task<IActionResult> Search(string author)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(author)) return BadRequest("Author Not Specified");
                var content = await _wikiService.SearchAuthor(author);
                if (string.IsNullOrEmpty(content)) return BadRequest("Error Retrieving Daily Author");
                return Content(content, "application/json");
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Searching Getting Daily Author: {ex.Message}");
            }
        }
    }
}
