using global::papermast.Data.Services;
using global::papermast.Entities.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class BooksApiController : ControllerBase
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly IUserService _userService;
        private readonly IBooksApiService _booksApiService;

        public BooksApiController(UserManager<ApplicationUser> userManager, IUserService userService, IBooksApiService booksApiService)
        {
            _userManager = userManager;
            _userService = userService;
            _booksApiService = booksApiService;
        }

        [HttpGet("search-daily")]
        public async Task<IActionResult> DailyAuthorSearch(string? text, string? intitle, string? inauthor,
                                                           string? subject, string? isbn)
        {
            try
            {
                var books = await _booksApiService.DailyAuthorSearch(text, intitle, inauthor, subject, isbn);
                if (!string.IsNullOrEmpty(books)) return Content(books, "application/json");
                return BadRequest($"Error Searching Daily Author Books");

            }
            catch(Exception ex)
            {
                return BadRequest($"Error Searching Daily Author Books: {ex.Message}");
            }
        }

        [Authorize(AuthenticationSchemes = "Bearer")]
        [HttpGet("search")]
        public async Task<IActionResult> Search(string? text, string? intitle, string? inauthor,
                                                string? subject, string? isbn)
        {
            try
            {
                var books = await _booksApiService.Search(text, intitle, inauthor, subject, isbn);
                if (!string.IsNullOrEmpty(books)) return Content(books, "application/json");
                return BadRequest($"Error Searching For Books");
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Searching For Books: {ex.Message}");
            }
        }
    }
}
