namespace papermast.Entities.Constants
{
    public static class BookStatus
    {
        public const string NOT_INTERESTED = "Not Interested"; 
        public const string TO_BE_READ = "To Be Read"; 
        public const string READING = "Reading";
        public const string READ = "Read";
        public const string DID_NOT_FINISH= "Did Not Finish";

        public static readonly IReadOnlySet<string> All = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            NOT_INTERESTED,
            TO_BE_READ,
            READING,
            READ,
            DID_NOT_FINISH
        };

        public static bool IsValid(string? status) =>
            !string.IsNullOrWhiteSpace(status) && All.Contains(status);
    }
}
