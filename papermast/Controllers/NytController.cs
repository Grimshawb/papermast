using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;

namespace papermast.Controllers
{

    [Route("api/[controller]")]
    [ApiController]
    public class NytController : ControllerBase
    {
        public readonly INytService _nytService;

        public NytController(INytService nytService)
        {
            _nytService = nytService;
        }

        [HttpGet("all-lists")]
        public async Task<IActionResult> GetAllBestSellerLists()
        {
            try
            {
                    return Content((await _nytService.GetAllBestSellerLists()) ?? "", "application/json");
            }
            catch (Exception ex)
            {
                return BadRequest($"Error Collecting Best Seller Lists: {ex.Message}");
            }
        }
    }
}
