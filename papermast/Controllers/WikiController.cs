using papermast.Data.Services;
using Microsoft.AspNetCore.Mvc;

namespace papermast.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class WikiController : ControllerBase
    {
        private readonly IWikiService _wikiService;

        public WikiController(IWikiService wikiService)
        {
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
