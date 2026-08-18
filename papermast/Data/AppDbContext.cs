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
    }
}
