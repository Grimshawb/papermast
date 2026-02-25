using global::papermast.Data.Services;
using global::papermast.Entities.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.WebUtilities;
using System.IdentityModel.Tokens.Jwt;
using System.Net.Http;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
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


        //[Authorize(AuthenticationSchemes = "Bearer")]
        [HttpGet("search")]
        public async Task<IActionResult> Search(string? text, string? intitle, string? inauthor,
                                                string? subject, string? isbn)
        {
            try
            {
                var apiKey = _config["GoogleBooks:ApiKey"];
                var apiUrl = _config["GoogleBooks:ApiUrl"];
                var queryParts = new List<string>();

                if (!string.IsNullOrEmpty(text)) queryParts.Add($"q:{text}");
                if (!string.IsNullOrEmpty(intitle)) queryParts.Add($"intitle:{intitle}");
                if (!string.IsNullOrEmpty(inauthor)) queryParts.Add($"inauthor:{inauthor}");
                if (!string.IsNullOrEmpty(subject)) queryParts.Add($"subject:{subject}");
                if (!string.IsNullOrEmpty(isbn)) queryParts.Add($"isbn:{isbn}");

                var query = queryParts.Count > 0 ? $"{string.Join("&", queryParts)}" : "";
                if (string.IsNullOrEmpty(query)) throw new Exception("Cannot Search With Empty Query");

                var queryParams = new Dictionary<string, string?>
                {
                    ["q"] = query,
                    ["orderBy"] = "relevance",
                    ["startIndex"] = "0",
                    ["maxResults"] = "40",
                    ["key"] = apiKey,
                };
                var url = QueryHelpers.AddQueryString(apiUrl, queryParams);
                var client = _httpClientFactory.CreateClient();
                var response = await client.GetAsync(url);
                //var response = await client.GetAsync($"{apiUrl}{query}&key={apiKey}");
                if (!response.IsSuccessStatusCode) return BadRequest($"Error Searching For Books: {response.StatusCode}");

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
