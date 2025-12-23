using System;
using System.IO;
using System.Security.Cryptography;

namespace MyJournalWPF.Services
{
    public class EncryptionService
    {
        private readonly byte[] _key;
        private const int KeySize = 32; // 256 bits
        private const int Iterations = 200000;

        public EncryptionService(string password, byte[] salt)
        {
            _key = DeriveKey(password, salt);
        }

        public static byte[] GenerateSalt()
        {
            return RandomNumberGenerator.GetBytes(16);
        }

        private static byte[] DeriveKey(string password, byte[] salt)
        {
            using var pbkdf2 = new Rfc2898DeriveBytes(
                password,
                salt,
                Iterations,
                HashAlgorithmName.SHA256);
            return pbkdf2.GetBytes(KeySize);
        }

        public byte[] Encrypt(string plainText)
        {
            if (string.IsNullOrEmpty(plainText))
                return Array.Empty<byte>();

            using var aes = Aes.Create();
            aes.Key = _key;
            aes.GenerateIV();

            using var encryptor = aes.CreateEncryptor();
            using var ms = new MemoryStream();
            
            ms.Write(aes.IV, 0, aes.IV.Length);
            
            using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
            using (var sw = new StreamWriter(cs))
            {
                sw.Write(plainText);
            }
            
            return ms.ToArray();
        }

        public string Decrypt(byte[] cipherText)
        {
            if (cipherText == null || cipherText.Length == 0)
                return string.Empty;

            using var aes = Aes.Create();
            aes.Key = _key;

            var iv = new byte[aes.IV.Length];
            Array.Copy(cipherText, 0, iv, 0, iv.Length);
            aes.IV = iv;

            using var decryptor = aes.CreateDecryptor();
            using var ms = new MemoryStream(cipherText, iv.Length, cipherText.Length - iv.Length);
            using var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read);
            using var sr = new StreamReader(cs);
            
            return sr.ReadToEnd();
        }

        public byte[] EncryptBytes(byte[] data)
        {
            if (data == null || data.Length == 0)
                return Array.Empty<byte>();

            using var aes = Aes.Create();
            aes.Key = _key;
            aes.GenerateIV();

            using var encryptor = aes.CreateEncryptor();
            using var ms = new MemoryStream();
            
            ms.Write(aes.IV, 0, aes.IV.Length);
            
            using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
            {
                cs.Write(data, 0, data.Length);
            }
            
            return ms.ToArray();
        }

        public byte[] DecryptBytes(byte[] cipherData)
        {
            if (cipherData == null || cipherData.Length == 0)
                return Array.Empty<byte>();

            using var aes = Aes.Create();
            aes.Key = _key;

            var iv = new byte[aes.IV.Length];
            Array.Copy(cipherData, 0, iv, 0, iv.Length);
            aes.IV = iv;

            using var decryptor = aes.CreateDecryptor();
            using var ms = new MemoryStream(cipherData, iv.Length, cipherData.Length - iv.Length);
            using var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read);
            using var output = new MemoryStream();
            
            cs.CopyTo(output);
            return output.ToArray();
        }
    }
}
