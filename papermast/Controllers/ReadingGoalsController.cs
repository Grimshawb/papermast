using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;
using papermast.Entities.DTO;
using System.Security.Claims;

namespace papermast.Controllers
{
    [Authorize(AuthenticationSchemes = "Bearer")]
    [Route("api/[controller]")]
    [ApiController]
    public class ReadingGoalsController : ControllerBase
    {
        private readonly IReadingGoalService _readingGoalService;

        public ReadingGoalsController(IReadingGoalService readingGoalService)
        {
            _readingGoalService = readingGoalService;
        }

        [HttpGet("{year:int}")]
        public async Task<ActionResult<ReadingGoalDto>> Get(int year)
        {
            try { return Ok(await _readingGoalService.Get(GetIdentityUserID(), year)); }
            catch (ArgumentException ex) { return BadRequest(ex.Message); }
        }

        [HttpPut]
        public async Task<ActionResult<ReadingGoalDto>> Upsert([FromBody] ReadingGoalRequest request)
        {
            try { return Ok(await _readingGoalService.Upsert(GetIdentityUserID(), request)); }
            catch (ArgumentException ex) { return BadRequest(ex.Message); }
        }

        private string GetIdentityUserID() =>
            User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? throw new UnauthorizedAccessException("The user identity is missing.");
    }
}
