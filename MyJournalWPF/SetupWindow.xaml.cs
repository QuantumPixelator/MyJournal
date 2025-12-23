using System;
using System.Drawing;
using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using MyJournalWPF.Models;
using MyJournalWPF.Services;
using OtpNet;
using QRCoder;

namespace MyJournalWPF
{
    public partial class SetupWindow : Window
    {
        private readonly JournalDbContext _dbContext;
        private string _totpSecret;

        public SetupWindow()
        {
            InitializeComponent();
            _dbContext = new JournalDbContext();
            GenerateTotpSecret();
        }

        private void GenerateTotpSecret()
        {
            _totpSecret = Base32Encoding.ToString(KeyGeneration.GenerateRandomKey(20));
            var totpUri = $"otpauth://totp/MyJournal?secret={_totpSecret}&issuer=MyJournal";
            
            using (var qrGenerator = new QRCodeGenerator())
            {
                var qrCodeData = qrGenerator.CreateQrCode(totpUri, QRCodeGenerator.ECCLevel.Q);
                using (var qrCode = new QRCode(qrCodeData))
                {
                    using (var qrBitmap = qrCode.GetGraphic(10))
                    {
                        QrCodeImage.Source = ConvertBitmapToImageSource(qrBitmap);
                    }
                }
            }
        }

        private BitmapImage ConvertBitmapToImageSource(Bitmap bitmap)
        {
            using (var memory = new MemoryStream())
            {
                bitmap.Save(memory, System.Drawing.Imaging.ImageFormat.Png);
                memory.Position = 0;
                
                var bitmapImage = new BitmapImage();
                bitmapImage.BeginInit();
                bitmapImage.StreamSource = memory;
                bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                bitmapImage.EndInit();
                bitmapImage.Freeze();
                
                return bitmapImage;
            }
        }

        private void CompleteSetup_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(PasswordBox.Password))
            {
                MessageBox.Show("Please enter a password.", "Error", 
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (PasswordBox.Password != ConfirmPasswordBox.Password)
            {
                MessageBox.Show("Passwords do not match.", "Error", 
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            try
            {
                var salt = EncryptionService.GenerateSalt();
                var encryption = new EncryptionService(PasswordBox.Password, salt);
                
                var config = new Config
                {
                    Id = 1,
                    Salt = salt,
                    EncryptedTotpSecret = encryption.Encrypt(_totpSecret)
                };

                _dbContext.Configs.Add(config);
                _dbContext.SaveChanges();

                MessageBox.Show("Setup completed successfully! Please use your authenticator app to log in.", 
                    "Success", MessageBoxButton.OK, MessageBoxImage.Information);

                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error during setup: {ex.Message}", "Error", 
                    MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
