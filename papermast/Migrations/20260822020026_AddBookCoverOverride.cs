using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace papermast.Migrations
{
    /// <inheritdoc />
    public partial class AddBookCoverOverride : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "CoverOverrideUrl",
                table: "BookMetadata",
                type: "varchar(2000)",
                maxLength: 2000,
                nullable: true)
                .Annotation("MySql:CharSet", "utf8mb4");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "CoverOverrideUrl",
                table: "BookMetadata");
        }
    }
}
