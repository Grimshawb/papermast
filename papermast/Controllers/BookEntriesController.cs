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
    public class BookEntriesController : ControllerBase
    {
        private readonly IBookEntryService _bookEntryService;

        public BookEntriesController(IBookEntryService bookEntryService)
        {
            _bookEntryService = bookEntryService;
        }

        [HttpGet]
        public async Task<ActionResult<IReadOnlyList<BookEntryDto>>> GetAll()
        {
            return Ok(await _bookEntryService.GetAll(GetIdentityUserID()));
        }

        [HttpPost]
        public async Task<ActionResult<BookEntryDto>> Create([FromBody] BookEntryRequest request)
        {
            try
            {
                var entry = await _bookEntryService.Create(GetIdentityUserID(), request);
                return Ok(entry);
            }
            catch (ArgumentException ex)
            {
                return BadRequest(ex.Message);
            }
            catch (InvalidOperationException ex)
            {
                return Conflict(ex.Message);
            }
        }

        [HttpPut("{entryID}")]
        public async Task<ActionResult<BookEntryDto>> Update(uint entryID, [FromBody] BookEntryRequest request)
        {
            try
            {
                var entry = await _bookEntryService.Update(GetIdentityUserID(), entryID, request);
                return entry is null ? NotFound() : Ok(entry);
            }
            catch (ArgumentException ex)
            {
                return BadRequest(ex.Message);
            }
            catch (InvalidOperationException ex)
            {
                return Conflict(ex.Message);
            }
        }

        private string GetIdentityUserID() =>
            User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? throw new UnauthorizedAccessException("The user identity is missing.");
    }
}
