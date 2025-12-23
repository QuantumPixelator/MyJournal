using System;
using System.Linq;
using System.Windows;
using MyJournalWPF.Services;
using OtpNet;

namespace MyJournalWPF
{
    public partial class LoginWindow : Window
    {
        private readonly JournalDbContext _dbContext;
        private int _attemptCount = 0;
        private const int MaxAttempts = 5;

        public EncryptionService? EncryptionKey { get; private set; }

        public LoginWindow(JournalDbContext dbContext)
        {
            InitializeComponent();
            _dbContext = dbContext;
            
            // Set focus to password box
            Loaded += (s, e) => PasswordBox.Focus();
        }

        private void Login_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(PasswordBox.Password) || 
                string.IsNullOrWhiteSpace(TotpCodeBox.Text))
            {
                ErrorTextBlock.Text = "Please enter both password and authenticator code.";
                return;
            }

            try
            {
                var config = _dbContext.Configs.FirstOrDefault();
                if (config == null)
                {
                    ErrorTextBlock.Text = "Configuration not found. Please run setup.";
                    return;
                }

                // Verify password by attempting to decrypt TOTP secret
                var encryption = new EncryptionService(PasswordBox.Password, config.Salt);
                string totpSecret;
                
                try
                {
                    totpSecret = encryption.Decrypt(config.EncryptedTotpSecret);
                }
                catch
                {
                    HandleFailedAttempt("Invalid password.");
                    return;
                }

                // Verify TOTP code
                var totp = new Totp(Base32Encoding.ToBytes(totpSecret));
                if (!totp.VerifyTotp(TotpCodeBox.Text, out _, new VerificationWindow(2, 2)))
                {
                    HandleFailedAttempt("Invalid authenticator code.");
                    return;
                }

                // Login successful
                EncryptionKey = encryption;
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                ErrorTextBlock.Text = $"Login error: {ex.Message}";
            }
        }

        private void HandleFailedAttempt(string message)
        {
            _attemptCount++;
            var remaining = MaxAttempts - _attemptCount;

            if (_attemptCount >= MaxAttempts)
            {
                MessageBox.Show("Too many failed login attempts. Application will exit.", 
                    "Login Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                Application.Current.Shutdown();
            }
            else
            {
                ErrorTextBlock.Text = $"{message} Attempts remaining: {remaining}";
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
