using System;
using System.Windows;

namespace MyJournalWPF
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            // Initialize database
            var dbContext = new JournalDbContext();
            dbContext.Database.EnsureCreated();

            // Check if first run
            if (dbContext.IsNewDatabase())
            {
                var setupWindow = new SetupWindow();
                if (setupWindow.ShowDialog() == true)
                {
                    // Setup completed, show login
                    ShowLoginWindow(dbContext);
                }
                else
                {
                    Shutdown();
                }
            }
            else
            {
                ShowLoginWindow(dbContext);
            }
        }

        private void ShowLoginWindow(JournalDbContext dbContext)
        {
            var loginWindow = new LoginWindow(dbContext);
            if (loginWindow.ShowDialog() == true)
            {
                var mainWindow = new MainWindow(dbContext, loginWindow.EncryptionKey);
                mainWindow.Show();
            }
            else
            {
                Shutdown();
            }
        }
    }
}
