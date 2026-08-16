namespace papermast.Entities.DTO
{
    public class ReadingGoalDto
    {
        public int Year { get; set; }
        public int TargetBookCount { get; set; }
        public int CompletedBookCount { get; set; }
    }

    public class ReadingGoalRequest
    {
        public int Year { get; set; }
        public int TargetBookCount { get; set; }
    }
}
