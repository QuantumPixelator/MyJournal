using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;
using MyJournalWPF.Models;
using MyJournalWPF.Services;

namespace MyJournalWPF
{
    public partial class MainWindow : Window
    {
        private readonly JournalDbContext _dbContext;
        private readonly EncryptionService _encryptionService;
        private Entry? _currentEntry;
        private List<Entry> _allEntries;

        public MainWindow(JournalDbContext dbContext, EncryptionService encryptionService)
        {
            InitializeComponent();
            _dbContext = dbContext;
            _encryptionService = encryptionService;
            _allEntries = new List<Entry>();

            InitializeFontComboBox();
            LoadEntries();
            
            // Apply keyboard shortcuts
            this.PreviewKeyDown += MainWindow_PreviewKeyDown;
        }

        private void MainWindow_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (e.Key == System.Windows.Input.Key.S && 
                (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Control) == System.Windows.Input.ModifierKeys.Control)
            {
                SaveEntry_Click(sender, e);
                e.Handled = true;
            }
            else if (e.Key == System.Windows.Input.Key.N && 
                     (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Control) == System.Windows.Input.ModifierKeys.Control)
            {
                NewEntry_Click(sender, e);
                e.Handled = true;
            }
        }

        private void InitializeFontComboBox()
        {
            foreach (var fontFamily in Fonts.SystemFontFamilies.OrderBy(f => f.Source))
            {
                FontFamilyComboBox.Items.Add(fontFamily.Source);
            }
            FontFamilyComboBox.SelectedItem = "Segoe UI";
        }

        private void LoadEntries()
        {
            _allEntries = _dbContext.Entries
                .Include(e => e.Attachments)
                .OrderByDescending(e => e.Date)
                .ToList();

            // Decrypt entries
            foreach (var entry in _allEntries)
            {
                if (entry.EncryptedTitle != null)
                    entry.Title = _encryptionService.Decrypt(entry.EncryptedTitle);
                if (entry.EncryptedContent != null)
                    entry.Content = _encryptionService.Decrypt(entry.EncryptedContent);
                if (entry.EncryptedTags != null)
                    entry.Tags = _encryptionService.Decrypt(entry.EncryptedTags);
            }

            UpdateEntriesList(_allEntries);
        }

        private void UpdateEntriesList(IEnumerable<Entry> entries)
        {
            EntriesListBox.ItemsSource = entries.OrderByDescending(e => e.Date).ToList();
        }

        private void NewEntry_Click(object sender, RoutedEventArgs e)
        {
            _currentEntry = new Entry
            {
                Date = DateTime.Now,
                FontFamily = FontFamilyComboBox.SelectedItem?.ToString() ?? "Segoe UI",
                FontSize = int.Parse((FontSizeComboBox.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "12")
            };

            TitleTextBox.Clear();
            ContentRichTextBox.Document.Blocks.Clear();
            ContentRichTextBox.Document.Blocks.Add(new Paragraph(new Run("")));
            TagsTextBox.Clear();
            AttachmentsListBox.ItemsSource = null;
        }

        private void SaveEntry_Click(object sender, RoutedEventArgs e)
        {
            if (_currentEntry == null)
            {
                MessageBox.Show("Please create or select an entry first.", "No Entry", 
                    MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            if (string.IsNullOrWhiteSpace(TitleTextBox.Text))
            {
                MessageBox.Show("Please enter a title for the entry.", "Missing Title", 
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _currentEntry.Title = TitleTextBox.Text;
            _currentEntry.Tags = TagsTextBox.Text;
            _currentEntry.LastSaved = DateTime.Now;

            // Get RTF content
            var textRange = new TextRange(ContentRichTextBox.Document.ContentStart, 
                ContentRichTextBox.Document.ContentEnd);
            using (var ms = new MemoryStream())
            {
                textRange.Save(ms, DataFormats.Rtf);
                _currentEntry.Content = System.Text.Encoding.UTF8.GetString(ms.ToArray());
            }

            // Encrypt fields
            _currentEntry.EncryptedTitle = _encryptionService.Encrypt(_currentEntry.Title);
            _currentEntry.EncryptedContent = _encryptionService.Encrypt(_currentEntry.Content);
            _currentEntry.EncryptedTags = _encryptionService.Encrypt(_currentEntry.Tags);

            if (_currentEntry.Id == 0)
            {
                _dbContext.Entries.Add(_currentEntry);
                _allEntries.Add(_currentEntry);
            }
            else
            {
                _dbContext.Entries.Update(_currentEntry);
            }

            _dbContext.SaveChanges();
            LoadEntries();

            MessageBox.Show("Entry saved successfully!", "Saved", 
                MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void DeleteEntry_Click(object sender, RoutedEventArgs e)
        {
            if (_currentEntry == null || _currentEntry.Id == 0)
            {
                MessageBox.Show("No entry selected.", "Error", 
                    MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var result = MessageBox.Show($"Are you sure you want to delete '{_currentEntry.Title}'?", 
                "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result == MessageBoxResult.Yes)
            {
                _dbContext.Entries.Remove(_currentEntry);
                _dbContext.SaveChanges();
                _allEntries.Remove(_currentEntry);
                
                NewEntry_Click(sender, e);
                LoadEntries();
            }
        }

        private void EntriesListBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (EntriesListBox.SelectedItem is Entry entry)
            {
                _currentEntry = entry;
                TitleTextBox.Text = entry.Title;
                TagsTextBox.Text = entry.Tags;

                // Load RTF content
                if (!string.IsNullOrEmpty(entry.Content))
                {
                    try
                    {
                        var textRange = new TextRange(ContentRichTextBox.Document.ContentStart, 
                            ContentRichTextBox.Document.ContentEnd);
                        using (var ms = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(entry.Content)))
                        {
                            textRange.Load(ms, DataFormats.Rtf);
                        }
                    }
                    catch
                    {
                        ContentRichTextBox.Document.Blocks.Clear();
                        ContentRichTextBox.Document.Blocks.Add(new Paragraph(new Run(entry.Content)));
                    }
                }

                AttachmentsListBox.ItemsSource = entry.Attachments;
            }
        }

        private void Calendar_SelectedDatesChanged(object sender, SelectionChangedEventArgs e)
        {
            if (EntryCalendar.SelectedDate.HasValue)
            {
                var selectedDate = EntryCalendar.SelectedDate.Value.Date;
                var filtered = _allEntries.Where(e => e.Date.Date == selectedDate).ToList();
                UpdateEntriesList(filtered);
            }
        }

        private void Search_TextChanged(object sender, TextChangedEventArgs e)
        {
            var searchText = SearchTextBox.Text.ToLower();
            if (string.IsNullOrWhiteSpace(searchText))
            {
                UpdateEntriesList(_allEntries);
                return;
            }

            var filtered = _allEntries.Where(entry =>
                entry.Title.ToLower().Contains(searchText) ||
                entry.Content.ToLower().Contains(searchText) ||
                entry.Tags.ToLower().Contains(searchText)
            ).ToList();

            UpdateEntriesList(filtered);
        }

        private void Bold_Click(object sender, RoutedEventArgs e)
        {
            var selection = ContentRichTextBox.Selection;
            if (!selection.IsEmpty)
            {
                var currentWeight = selection.GetPropertyValue(TextElement.FontWeightProperty);
                var newWeight = currentWeight.Equals(FontWeights.Bold) ? FontWeights.Normal : FontWeights.Bold;
                selection.ApplyPropertyValue(TextElement.FontWeightProperty, newWeight);
            }
        }

        private void Italic_Click(object sender, RoutedEventArgs e)
        {
            var selection = ContentRichTextBox.Selection;
            if (!selection.IsEmpty)
            {
                var currentStyle = selection.GetPropertyValue(TextElement.FontStyleProperty);
                var newStyle = currentStyle.Equals(FontStyles.Italic) ? FontStyles.Normal : FontStyles.Italic;
                selection.ApplyPropertyValue(TextElement.FontStyleProperty, newStyle);
            }
        }

        private void Underline_Click(object sender, RoutedEventArgs e)
        {
            var selection = ContentRichTextBox.Selection;
            if (!selection.IsEmpty)
            {
                var currentDecoration = selection.GetPropertyValue(Inline.TextDecorationsProperty);
                var newDecoration = currentDecoration.Equals(TextDecorations.Underline) ? null : TextDecorations.Underline;
                selection.ApplyPropertyValue(Inline.TextDecorationsProperty, newDecoration);
            }
        }

        private void Color_Click(object sender, RoutedEventArgs e)
        {
            var colorDialog = new System.Windows.Forms.ColorDialog();
            if (colorDialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            {
                var color = Color.FromArgb(colorDialog.Color.A, colorDialog.Color.R, 
                    colorDialog.Color.G, colorDialog.Color.B);
                ContentRichTextBox.Selection.ApplyPropertyValue(TextElement.ForegroundProperty, 
                    new SolidColorBrush(color));
            }
        }

        private void FontFamily_Changed(object sender, SelectionChangedEventArgs e)
        {
            if (FontFamilyComboBox.SelectedItem != null && ContentRichTextBox != null)
            {
                var fontFamily = new FontFamily(FontFamilyComboBox.SelectedItem.ToString()!);
                ContentRichTextBox.Selection.ApplyPropertyValue(TextElement.FontFamilyProperty, fontFamily);
            }
        }

        private void FontSize_Changed(object sender, SelectionChangedEventArgs e)
        {
            if (FontSizeComboBox.SelectedItem is ComboBoxItem item && ContentRichTextBox != null)
            {
                var size = double.Parse(item.Content.ToString()!);
                ContentRichTextBox.Selection.ApplyPropertyValue(TextElement.FontSizeProperty, size);
            }
        }

        private void InsertImage_Click(object sender, RoutedEventArgs e)
        {
            var openFileDialog = new OpenFileDialog
            {
                Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.bmp",
                Title = "Select an Image"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                try
                {
                    var image = new Image
                    {
                        Source = new BitmapImage(new Uri(openFileDialog.FileName)),
                        MaxWidth = 400,
                        Stretch = Stretch.Uniform
                    };

                    var container = new InlineUIContainer(image, ContentRichTextBox.CaretPosition);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Error inserting image: {ex.Message}", "Error", 
                        MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void AttachFile_Click(object sender, RoutedEventArgs e)
        {
            if (_currentEntry == null)
            {
                NewEntry_Click(sender, e);
            }

            var openFileDialog = new OpenFileDialog
            {
                Title = "Select File to Attach"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                var fileData = File.ReadAllBytes(openFileDialog.FileName);
                var attachment = new Attachment
                {
                    FileName = Path.GetFileName(openFileDialog.FileName),
                    EncryptedData = _encryptionService.EncryptBytes(fileData),
                    EntryId = _currentEntry!.Id
                };

                _currentEntry.Attachments.Add(attachment);
                AttachmentsListBox.ItemsSource = null;
                AttachmentsListBox.ItemsSource = _currentEntry.Attachments;
            }
        }

        private void ExportEntry_Click(object sender, RoutedEventArgs e)
        {
            if (_currentEntry == null)
            {
                MessageBox.Show("No entry selected.", "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var saveFileDialog = new SaveFileDialog
            {
                Filter = "HTML Files|*.html",
                FileName = $"{_currentEntry.Title}.html"
            };

            if (saveFileDialog.ShowDialog() == true)
            {
                var html = $@"
<!DOCTYPE html>
<html>
<head>
    <title>{_currentEntry.Title}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2C3E50; }}
        .date {{ color: #7F8C8D; font-size: 14px; }}
        .content {{ margin-top: 20px; line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>{_currentEntry.Title}</h1>
    <div class='date'>{_currentEntry.Date:MMMM dd, yyyy}</div>
    <div class='content'>{_currentEntry.Content}</div>
</body>
</html>";
                File.WriteAllText(saveFileDialog.FileName, html);
                MessageBox.Show("Entry exported successfully!", "Success", 
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void BackupDatabase_Click(object sender, RoutedEventArgs e)
        {
            var saveFileDialog = new SaveFileDialog
            {
                Filter = "Database Files|*.db",
                FileName = $"myjournal_backup_{DateTime.Now:yyyyMMdd_HHmmss}.db"
            };

            if (saveFileDialog.ShowDialog() == true)
            {
                File.Copy("myjournal.db", saveFileDialog.FileName, true);
                MessageBox.Show("Database backed up successfully!", "Success", 
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void Settings_Click(object sender, RoutedEventArgs e)
        {
            var settingsWindow = new SettingsWindow();
            settingsWindow.ShowDialog();
        }

        private void DiscardChanges_Click(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show("Are you sure you want to discard changes?", 
                "Discard Changes", MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result == MessageBoxResult.Yes)
            {
                if (_currentEntry != null && _currentEntry.Id > 0)
                {
                    // Reload the entry
                    EntriesListBox_SelectionChanged(sender, new SelectionChangedEventArgs(e.RoutedEvent, 
                        new List<object>(), new List<object> { _currentEntry }));
                }
                else
                {
                    NewEntry_Click(sender, e);
                }
            }
        }

        private void Exit_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void ContentRichTextBox_SelectionChanged(object sender, RoutedEventArgs e)
        {
            // Update formatting buttons based on selection
            var selection = ContentRichTextBox.Selection;
            if (!selection.IsEmpty)
            {
                var weight = selection.GetPropertyValue(TextElement.FontWeightProperty);
                BoldButton.IsChecked = weight.Equals(FontWeights.Bold);

                var style = selection.GetPropertyValue(TextElement.FontStyleProperty);
                ItalicButton.IsChecked = style.Equals(FontStyles.Italic);

                var decoration = selection.GetPropertyValue(Inline.TextDecorationsProperty);
                UnderlineButton.IsChecked = decoration != null && decoration.Equals(TextDecorations.Underline);
            }
        }
    }
}
