using global::papermast.Data.Services;
using global::papermast.Entities.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using System.IdentityModel.Tokens.Jwt;
using System.Net.Http;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize(AuthenticationSchemes = "Bearer")]
    public class BooksAPIController : ControllerBase
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IConfiguration _config;
        private readonly IUserService _userService;

        public BooksAPIController(UserManager<ApplicationUser> userManager, IConfiguration config, IUserService userService, IHttpClientFactory httpClientFactory)
        {
            _userManager = userManager;
            _config = config;
            _userService = userService;
            _httpClientFactory = httpClientFactory;
        }


        [HttpGet("search")]
        public async Task<IActionResult> Search(string query)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(query)) return BadRequest("Query is required");

                var apiKey = _config["GoogleBooks:ApiKey"];
                var apiUrl = _config["GoogleBooks:ApiUrl"];

                var client = _httpClientFactory.CreateClient();
                var response = await client.GetAsync($"{apiUrl}?q={query}&key={apiKey}");

                if (!response.IsSuccessStatusCode) return StatusCode((int)response.StatusCode);

                var content = await response.Content.ReadAsStringAsync();
                return Content(content, "application/json");
            }
            catch(Exception ex)
            {
                return BadRequest($"Error Searching For Books: {ex.Message}");
            }
        }
    }
}
