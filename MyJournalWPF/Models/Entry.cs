using System;
using System.Collections.Generic;

namespace MyJournalWPF.Models
{
    public class Entry
    {
        public int Id { get; set; }
        public DateTime Date { get; set; }
        public string Title { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
        public string Tags { get; set; } = string.Empty;
        public string? FontFamily { get; set; }
        public int? FontSize { get; set; }
        public DateTime? LastSaved { get; set; }
        
        // Encrypted fields (stored in DB)
        public byte[]? EncryptedTitle { get; set; }
        public byte[]? EncryptedContent { get; set; }
        public byte[]? EncryptedTags { get; set; }
        
        public virtual ICollection<Attachment> Attachments { get; set; } = new List<Attachment>();
    }

    public class Attachment
    {
        public int Id { get; set; }
        public int EntryId { get; set; }
        public string FileName { get; set; } = string.Empty;
        public byte[] EncryptedData { get; set; } = Array.Empty<byte>();
        
        public virtual Entry? Entry { get; set; }
    }

    public class Config
    {
        public int Id { get; set; }
        public byte[] Salt { get; set; } = Array.Empty<byte>();
        public byte[] EncryptedTotpSecret { get; set; } = Array.Empty<byte>();
    }
}
