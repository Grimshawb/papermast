using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace papermast.Migrations
{
    [DbContext(typeof(AppDbContext))]
    [Migration("20260815000000_AddBookEntryMetadata")]
    public partial class AddBookEntryMetadata : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>("Authors", "BookEntries", "varchar(1000)", maxLength: 1000, nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
            migrationBuilder.AddColumn<DateTime>("CreatedDate", "BookEntries", "datetime(6)", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP(6)");
            migrationBuilder.AddColumn<string>("Source", "BookEntries", "varchar(100)", maxLength: 100, nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
            migrationBuilder.AddColumn<string>("SourceBookID", "BookEntries", "varchar(200)", maxLength: 200, nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
            migrationBuilder.AddColumn<int>("PageCount", "BookEntries", "int", nullable: false, defaultValue: 0);
            migrationBuilder.AddColumn<string>("ThumbnailUrl", "BookEntries", "varchar(2000)", maxLength: 2000, nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
            migrationBuilder.AddColumn<string>("Title", "BookEntries", "varchar(500)", maxLength: 500, nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
            migrationBuilder.AddColumn<DateTime>("UpdatedDate", "BookEntries", "datetime(6)", nullable: false, defaultValueSql: "CURRENT_TIMESTAMP(6)");

            migrationBuilder.Sql("UPDATE BookEntries SET Source = 'legacy', SourceBookID = CONCAT('entry-', EntryID), Title = 'Unknown title' WHERE Title IS NULL");
            migrationBuilder.AlterColumn<string>("Title", "BookEntries", "varchar(500)", maxLength: 500, nullable: false, oldClrType: typeof(string), oldType: "varchar(500)", oldMaxLength: 500, oldNullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");

            migrationBuilder.CreateIndex(
                name: "IX_BookEntries_UserID_Source_SourceBookID",
                table: "BookEntries",
                columns: new[] { "UserID", "Source", "SourceBookID" },
                unique: true);
            migrationBuilder.CreateIndex("IX_BookEntries_UserID_Isbn10", "BookEntries", new[] { "UserID", "Isbn10" });
            migrationBuilder.CreateIndex("IX_BookEntries_UserID_Isbn13", "BookEntries", new[] { "UserID", "Isbn13" });
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex("IX_BookEntries_UserID_Source_SourceBookID", "BookEntries");
            migrationBuilder.DropIndex("IX_BookEntries_UserID_Isbn10", "BookEntries");
            migrationBuilder.DropIndex("IX_BookEntries_UserID_Isbn13", "BookEntries");
            migrationBuilder.DropColumn("Authors", "BookEntries");
            migrationBuilder.DropColumn("CreatedDate", "BookEntries");
            migrationBuilder.DropColumn("Source", "BookEntries");
            migrationBuilder.DropColumn("SourceBookID", "BookEntries");
            migrationBuilder.DropColumn("PageCount", "BookEntries");
            migrationBuilder.DropColumn("ThumbnailUrl", "BookEntries");
            migrationBuilder.DropColumn("Title", "BookEntries");
            migrationBuilder.DropColumn("UpdatedDate", "BookEntries");
        }
    }
}
