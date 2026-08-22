using System;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace papermast.Migrations
{
    /// <inheritdoc />
    public partial class AddCuratedCatalog : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "CuratedCatalogBatches",
                columns: table => new
                {
                    CuratedCatalogBatchID = table.Column<int>(type: "int", nullable: false)
                        .Annotation("MySql:ValueGenerationStrategy", MySqlValueGenerationStrategy.IdentityColumn),
                    GenreSlug = table.Column<string>(type: "varchar(64)", maxLength: 64, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Status = table.Column<string>(type: "varchar(16)", maxLength: 16, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    CreatedAtUtc = table.Column<DateTime>(type: "datetime(6)", nullable: false),
                    PublishedAtUtc = table.Column<DateTime>(type: "datetime(6)", nullable: true),
                    CreatedByUserID = table.Column<string>(type: "varchar(255)", maxLength: 255, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CuratedCatalogBatches", x => x.CuratedCatalogBatchID);
                })
                .Annotation("MySql:CharSet", "utf8mb4");

            migrationBuilder.CreateTable(
                name: "CuratedCatalogBooks",
                columns: table => new
                {
                    CuratedCatalogBookID = table.Column<int>(type: "int", nullable: false)
                        .Annotation("MySql:ValueGenerationStrategy", MySqlValueGenerationStrategy.IdentityColumn),
                    CuratedCatalogBatchID = table.Column<int>(type: "int", nullable: false),
                    Section = table.Column<string>(type: "varchar(32)", maxLength: 32, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Position = table.Column<int>(type: "int", nullable: false),
                    Isbn13 = table.Column<string>(type: "varchar(13)", maxLength: 13, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    SourceBookID = table.Column<string>(type: "varchar(255)", maxLength: 255, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Title = table.Column<string>(type: "varchar(500)", maxLength: 500, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    AuthorsJson = table.Column<string>(type: "longtext", nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Description = table.Column<string>(type: "longtext", nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    CoverUrl = table.Column<string>(type: "varchar(1000)", maxLength: 1000, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Publisher = table.Column<string>(type: "varchar(255)", maxLength: 255, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    IdentifiersJson = table.Column<string>(type: "longtext", nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    PublishedDate = table.Column<string>(type: "varchar(32)", maxLength: 32, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    ReleaseDate = table.Column<DateTime>(type: "datetime(6)", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CuratedCatalogBooks", x => x.CuratedCatalogBookID);
                    table.ForeignKey(
                        name: "FK_CuratedCatalogBooks_CuratedCatalogBatches_CuratedCatalogBatc~",
                        column: x => x.CuratedCatalogBatchID,
                        principalTable: "CuratedCatalogBatches",
                        principalColumn: "CuratedCatalogBatchID",
                        onDelete: ReferentialAction.Cascade);
                })
                .Annotation("MySql:CharSet", "utf8mb4");

            migrationBuilder.CreateIndex(
                name: "IX_CuratedCatalogBatches_GenreSlug_Status",
                table: "CuratedCatalogBatches",
                columns: new[] { "GenreSlug", "Status" });

            migrationBuilder.CreateIndex(
                name: "IX_CuratedCatalogBooks_CuratedCatalogBatchID_Isbn13",
                table: "CuratedCatalogBooks",
                columns: new[] { "CuratedCatalogBatchID", "Isbn13" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_CuratedCatalogBooks_CuratedCatalogBatchID_Section_Position",
                table: "CuratedCatalogBooks",
                columns: new[] { "CuratedCatalogBatchID", "Section", "Position" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "CuratedCatalogBooks");

            migrationBuilder.DropTable(
                name: "CuratedCatalogBatches");
        }
    }
}
