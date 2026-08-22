using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using papermast.Entities.Models;
using System.Collections.Generic;
using System.Reflection.Emit;

public class AppDbContext : IdentityDbContext<ApplicationUser>
{
    public AppDbContext(DbContextOptions<AppDbContext> options)
        : base(options) { }

    public DbSet<AppUser> AppUsers { get; set; }
    public DbSet<BookEntry> BookEntries { get; set; }
    public DbSet<ReadingGoal> ReadingGoals { get; set; }
    public DbSet<ApiRequestLog> ApiRequestLogs { get; set; }
    public DbSet<CuratedCatalogBatch> CuratedCatalogBatches { get; set; }
    public DbSet<CuratedCatalogBook> CuratedCatalogBooks { get; set; }
    public DbSet<BookMetadata> BookMetadata { get; set; }

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        builder.Entity<AppUser>()
            .HasOne(a => a.IdentityUser)
            .WithOne()
            .HasForeignKey<AppUser>(a => a.IdentityUserId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.Entity<BookEntry>()
            .HasIndex(entry => new { entry.UserID, entry.Source, entry.SourceBookID })
            .IsUnique();

        builder.Entity<BookEntry>()
            .HasIndex(entry => new { entry.UserID, entry.Isbn13 });

        builder.Entity<BookEntry>()
            .HasIndex(entry => new { entry.UserID, entry.Isbn10 });

        builder.Entity<ReadingGoal>()
            .HasIndex(goal => new { goal.UserID, goal.Year })
            .IsUnique();

        builder.Entity<ApiRequestLog>(entry =>
        {
            entry.HasKey(log => log.ApiRequestLogID);
            entry.Property(log => log.ApiName).HasMaxLength(64);
            entry.Property(log => log.Direction).HasMaxLength(16);
            entry.Property(log => log.Method).HasMaxLength(16);
            entry.Property(log => log.Route).HasMaxLength(512);
            entry.Property(log => log.ActorType).HasMaxLength(16);
            entry.Property(log => log.ActorId).HasMaxLength(255);
            entry.Property(log => log.QueryParameterNames).HasMaxLength(512);
            entry.Property(log => log.ClientIp).HasMaxLength(45);
            entry.Property(log => log.UserAgent).HasMaxLength(512);
            entry.Property(log => log.TraceId).HasMaxLength(64);
            entry.Property(log => log.ErrorType).HasMaxLength(255);
            entry.Property(log => log.ErrorMessage).HasMaxLength(1000);
            entry.HasIndex(log => log.StartedAtUtc);
            entry.HasIndex(log => new { log.ApiName, log.StartedAtUtc });
            entry.HasIndex(log => new { log.ActorId, log.StartedAtUtc });
            entry.HasIndex(log => log.TraceId);
        });

        builder.Entity<CuratedCatalogBatch>(batch =>
        {
            batch.HasKey(item => item.CuratedCatalogBatchID);
            batch.Property(item => item.GenreSlug).HasMaxLength(64);
            batch.Property(item => item.Status).HasMaxLength(16);
            batch.Property(item => item.CreatedByUserID).HasMaxLength(255);
            batch.HasIndex(item => new { item.GenreSlug, item.Status });
        });

        builder.Entity<CuratedCatalogBook>(book =>
        {
            book.HasKey(item => item.CuratedCatalogBookID);
            book.Property(item => item.Section).HasMaxLength(32);
            book.Property(item => item.Isbn13).HasMaxLength(13);
            book.Property(item => item.SourceBookID).HasMaxLength(255);
            book.Property(item => item.Title).HasMaxLength(500);
            book.Property(item => item.Publisher).HasMaxLength(255);
            book.Property(item => item.CoverUrl).HasMaxLength(1000);
            book.Property(item => item.PublishedDate).HasMaxLength(32);
            book.HasIndex(item => new { item.CuratedCatalogBatchID, item.Section, item.Position }).IsUnique();
            book.HasIndex(item => new { item.CuratedCatalogBatchID, item.Isbn13 }).IsUnique();
            book.HasOne(item => item.Batch).WithMany(batch => batch.Books)
                .HasForeignKey(item => item.CuratedCatalogBatchID).OnDelete(DeleteBehavior.Cascade);
        });

        builder.Entity<BookMetadata>(metadata =>
        {
            metadata.HasKey(item => item.BookMetadataID);
            metadata.Property(item => item.Isbn13).HasMaxLength(13);
            metadata.Property(item => item.SourceBookID).HasMaxLength(255);
            metadata.Property(item => item.Title).HasMaxLength(500);
            metadata.Property(item => item.CoverUrl).HasMaxLength(1000);
            metadata.Property(item => item.CoverOverrideUrl).HasMaxLength(2000);
            metadata.Property(item => item.Publisher).HasMaxLength(255);
            metadata.Property(item => item.PublishedDate).HasMaxLength(32);
            metadata.Property(item => item.Provider).HasMaxLength(32);
            metadata.HasIndex(item => item.Isbn13).IsUnique();
        });
    }
}
