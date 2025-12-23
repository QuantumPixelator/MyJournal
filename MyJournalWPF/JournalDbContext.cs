using Microsoft.EntityFrameworkCore;
using MyJournalWPF.Models;
using System.Linq;

namespace MyJournalWPF
{
    public class JournalDbContext : DbContext
    {
        public DbSet<Entry> Entries { get; set; }
        public DbSet<Attachment> Attachments { get; set; }
        public DbSet<Config> Configs { get; set; }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite("Data Source=myjournal.db");
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.Entity<Entry>(entity =>
            {
                entity.HasKey(e => e.Id);
                entity.Property(e => e.Date).IsRequired();
                entity.Ignore(e => e.Title);
                entity.Ignore(e => e.Content);
                entity.Ignore(e => e.Tags);
            });

            modelBuilder.Entity<Attachment>(entity =>
            {
                entity.HasKey(a => a.Id);
                entity.HasOne(a => a.Entry)
                      .WithMany(e => e.Attachments)
                      .HasForeignKey(a => a.EntryId)
                      .OnDelete(DeleteBehavior.Cascade);
            });

            modelBuilder.Entity<Config>(entity =>
            {
                entity.HasKey(c => c.Id);
            });
        }

        public bool IsNewDatabase()
        {
            return !Configs.Any();
        }
    }
}
