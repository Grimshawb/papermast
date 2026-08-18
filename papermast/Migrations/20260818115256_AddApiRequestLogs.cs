using System;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace papermast.Migrations
{
    /// <inheritdoc />
    public partial class AddApiRequestLogs : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "ApiRequestLogs",
                columns: table => new
                {
                    ApiRequestLogID = table.Column<ulong>(type: "bigint unsigned", nullable: false)
                        .Annotation("MySql:ValueGenerationStrategy", MySqlValueGenerationStrategy.IdentityColumn),
                    StartedAtUtc = table.Column<DateTimeOffset>(type: "datetime(6)", nullable: false),
                    ApiName = table.Column<string>(type: "varchar(64)", maxLength: 64, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Direction = table.Column<string>(type: "varchar(16)", maxLength: 16, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Method = table.Column<string>(type: "varchar(16)", maxLength: 16, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    Route = table.Column<string>(type: "varchar(512)", maxLength: 512, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    StatusCode = table.Column<int>(type: "int", nullable: false),
                    DurationMs = table.Column<double>(type: "double", nullable: false),
                    ActorType = table.Column<string>(type: "varchar(16)", maxLength: 16, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    ActorId = table.Column<string>(type: "varchar(255)", maxLength: 255, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    QueryParameterNames = table.Column<string>(type: "varchar(512)", maxLength: 512, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    ClientIp = table.Column<string>(type: "varchar(45)", maxLength: 45, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    UserAgent = table.Column<string>(type: "varchar(512)", maxLength: 512, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    TraceId = table.Column<string>(type: "varchar(64)", maxLength: 64, nullable: false)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    ErrorType = table.Column<string>(type: "varchar(255)", maxLength: 255, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4"),
                    ErrorMessage = table.Column<string>(type: "varchar(1000)", maxLength: 1000, nullable: true)
                        .Annotation("MySql:CharSet", "utf8mb4")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ApiRequestLogs", x => x.ApiRequestLogID);
                })
                .Annotation("MySql:CharSet", "utf8mb4");

            migrationBuilder.CreateIndex(
                name: "IX_ApiRequestLogs_ActorId_StartedAtUtc",
                table: "ApiRequestLogs",
                columns: new[] { "ActorId", "StartedAtUtc" });

            migrationBuilder.CreateIndex(
                name: "IX_ApiRequestLogs_ApiName_StartedAtUtc",
                table: "ApiRequestLogs",
                columns: new[] { "ApiName", "StartedAtUtc" });

            migrationBuilder.CreateIndex(
                name: "IX_ApiRequestLogs_StartedAtUtc",
                table: "ApiRequestLogs",
                column: "StartedAtUtc");

            migrationBuilder.CreateIndex(
                name: "IX_ApiRequestLogs_TraceId",
                table: "ApiRequestLogs",
                column: "TraceId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ApiRequestLogs");
        }
    }
}
