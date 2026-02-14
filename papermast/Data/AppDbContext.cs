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

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        builder.Entity<AppUser>()
            .HasOne(a => a.IdentityUser)
            .WithOne()
            .HasForeignKey<AppUser>(a => a.IdentityUserId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
