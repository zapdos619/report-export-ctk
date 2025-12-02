# 📊 Salesforce Report Exporter

A powerful desktop application for bulk exporting Salesforce reports with **no 2,000 row limit**. Built with Python and CustomTkinter for a modern, responsive user experience.

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Key Features

### 🚀 **Performance & Scalability**
- **Virtual Scrolling** - Handle 10,000+ reports without UI freezing
- **Concurrent Downloads** - Export up to 10 reports simultaneously
- **Smart Caching** - Instant results for repeated searches
- **Background Processing** - UI stays responsive during long operations

### 🔍 **Powerful Search**
- **Keyword Search** - Find reports and folders by name
- **Real-time Results** - See matches instantly
- **Organized View** - Reports grouped by folder
- **Unified Public Folder** - Automatically groups orphaned public reports
- **Cache Management** - Stores last 10 searches for instant access

### 📦 **Export Capabilities**
- **No Row Limit** - Bypass Salesforce's 2,000 row API restriction
- **Dual Format Support** - Export as CSV or Excel (.xlsx)
- **Batch Export** - Select multiple reports at once
- **ZIP Packaging** - All reports bundled in a single file
- **Progress Tracking** - Real-time progress with ETA and speed
- **Error Recovery** - Retry failed exports automatically
- **Auto-rename** - Prevents filename conflicts automatically

### 🛡️ **Security & Reliability**
- **SOAP Authentication** - No Connected App required
- **Session Management** - Secure token-based authentication
- **Custom Domain Support** - Works with My Domain and custom URLs
- **Sandbox Support** - Connect to sandbox or production orgs
- **Thread-Safe Operations** - Prevents race conditions and crashes

### 🎨 **Modern UI**
- **Dark Mode** - Easy on the eyes
- **Responsive Design** - Optimized 1200×740 layout
- **Intuitive Layout** - Clean, organized interface
- **Keyboard Shortcuts** - `F5` to refresh, `Ctrl+E` to export, `ESC` to cancel
- **Activity Log** - Track all operations in real-time

---

## 📋 Requirements

- **Python 3.10 or higher**
- **Windows, macOS, or Linux**
- **Salesforce Account** with report access
- **Internet Connection** for API calls

---

## 🔧 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/salesforce-report-exporter.git
cd salesforce-report-exporter
```

### 2️⃣ Create Virtual Environment

#### **Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### **macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run the Application
```bash
python main.py
```

---

## 📦 Creating Portable Executable (.exe)

Want to distribute the app without requiring Python installation? Create a standalone executable!

### **Prerequisites**

Install PyInstaller:
```bash
pip install pyinstaller
```

### **Build Executable (Windows)**

#### **Option 1: Single File (Recommended)**
```bash
pyinstaller --onefile --windowed --name "SalesforceReportExporter" --icon=app_icon.ico main.py
```

#### **Option 2: Directory Bundle (Faster Startup)**
```bash
pyinstaller --onedir --windowed --name "SalesforceReportExporter" --icon=app_icon.ico main.py
```

### **Build Parameters Explained**
- `--onefile` - Packages everything into a single .exe file
- `--onedir` - Creates a folder with .exe and dependencies (faster startup)
- `--windowed` - No console window (GUI only)
- `--name` - Output executable name
- `--icon` - Application icon (optional, requires .ico file)

### **Output Location**
- **Single file:** `dist/SalesforceReportExporter.exe`
- **Directory:** `dist/SalesforceReportExporter/SalesforceReportExporter.exe`

### **Build for macOS**
```bash
pyinstaller --onefile --windowed --name "SalesforceReportExporter" main.py
```
Output: `dist/SalesforceReportExporter` (macOS app bundle)

### **Build for Linux**
```bash
pyinstaller --onefile --name "SalesforceReportExporter" main.py
```
Output: `dist/SalesforceReportExporter` (Linux executable)

### **Advanced: Custom Build Configuration**

Create a `build.spec` file for more control:
```bash
pyinstaller --name "SalesforceReportExporter" --windowed main.py
```

Then edit the generated `SalesforceReportExporter.spec` file and rebuild:
```bash
pyinstaller SalesforceReportExporter.spec
```

### **Troubleshooting Build Issues**

**Issue:** "Module not found" errors
```bash
# Solution: Reinstall dependencies and rebuild
pip install -r requirements.txt --force-reinstall
pyinstaller --clean SalesforceReportExporter.spec
```

**Issue:** Large file size (100MB+)
```bash
# Solution: Exclude unnecessary packages
pyinstaller --onefile --windowed --exclude-module matplotlib --exclude-module numpy main.py
```

**Issue:** Antivirus flags executable
- This is common with PyInstaller. Add exception in your antivirus software.
- Consider code signing the executable for distribution.

---

## 🚀 Quick Start Guide

### **Step 1: Login**

1. Launch the application
2. Select your environment:
   - **Production** - For live Salesforce org
   - **Sandbox** - For testing environments
   - **Custom Domain** - For My Domain or custom URLs
3. Enter your credentials:
   - **Username** - Your Salesforce email
   - **Password** - Your Salesforce password
   - **Security Token** - Optional if IP is whitelisted
4. Click **Login to Salesforce**

> 💡 **Tip:** Enable "Use Custom Domain" if your org uses My Domain (e.g., `mycompany.my.salesforce.com`)

---

### **Step 2: Search for Reports**

1. Enter keywords in the search box:
   - Examples: `"Sales"`, `"Q4 2024"`, `"Account"`
2. Click **🔍 Search** or press `Enter`
3. Browse results organized by folder
4. Expand folders to see individual reports

> 💡 **Tip:** Search results are cached - searching the same keyword again is instant!

> 💡 **Feature:** Public reports without folders are automatically grouped in "🌐 Unified Public Folder"

---

### **Step 3: Select Reports**

- **Check individual reports** - Click checkbox next to report name
- **Select entire folder** - Click checkbox next to folder name
- **Clear all** - Click "Clear All Selected" button

> 💡 **Tip:** Selected reports appear in the right panel for easy review

---

### **Step 4: Export**

1. **Choose format:**
   - **CSV** - Fast, recommended for large exports
   - **Excel** - Formatted .xlsx files (requires `openpyxl`)

2. Click **Browse** to choose save location

3. (Optional) Edit the ZIP filename

4. Click **🚀 Export Reports** or press `Ctrl+E`

5. Wait for progress to complete

6. Open the exported ZIP file

> 💡 **Tip:** Press `ESC` to cancel an export in progress

> 💡 **Tip:** If a file already exists, it will be auto-renamed (e.g., `report_1.zip`, `report_2.zip`)

---

## 🎯 Advanced Usage

### **Keyboard Shortcuts**

| Shortcut | Action |
|----------|--------|
| `Enter` | Execute search / Login |
| `F5` | Refresh search results |
| `Ctrl+E` | Start export |
| `ESC` | Cancel current operation |

---

### **Search Tips**

- **Broad keywords** - `"Sales"` finds all sales-related reports
- **Specific names** - `"Q4 Revenue Report"` finds exact matches
- **Partial matches** - `"Rev"` finds "Revenue", "Review", etc.
- **Case insensitive** - `"SALES"` and `"sales"` work the same

---

### **Export Formats**

#### **CSV Format**
- ✅ Fast export (recommended for 1000+ reports)
- ✅ Small file size
- ✅ Works with all tools (Excel, Google Sheets, Python, R)
- ✅ No dependencies required

#### **Excel Format (.xlsx)**
- ✅ Professional formatting
- ✅ Easier to open (no import steps)
- ✅ Includes styled headers
- ✅ Auto-sized columns
- ⚠️ Requires `openpyxl` library
- ⚠️ Slower for large reports

**Install Excel support:**
```bash
pip install openpyxl
```

---

### **Export Performance**

#### **Concurrent Downloads**
The app downloads up to 10 reports simultaneously:
- Small exports (1-10 reports): ~5-10 seconds
- Medium exports (50 reports): ~30-60 seconds
- Large exports (500+ reports): ~3-5 minutes
- Very large (5000+ reports): ~20-30 minutes

#### **Progress Tracking**
Real-time metrics during export:
- **Reports/Second** - Current download speed
- **ETA** - Estimated time remaining
- **Percentage** - Overall completion status

#### **Error Handling**
Failed reports are:
- ✅ Logged in the activity log
- ✅ Saved with error details in the ZIP
- ✅ Listed in the export summary file
- ✅ Automatically retried (up to 3 attempts)

---

## 📂 Project Structure
```
salesforce-report-exporter/
│
├── main.py                 # Application entry point
├── main_app.py            # Main application window
├── login_window.py        # Login interface
├── exporter.py            # Salesforce API logic
├── salesforce_auth.py     # SOAP authentication
├── virtual_tree.py        # Virtual scrolling tree view
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore            # Git ignore rules
└── build/                # Build artifacts (created by PyInstaller)
    └── SalesforceReportExporter/
```

---

## 🔐 Authentication & Security

### **How Authentication Works**

1. **SOAP Login** - Uses Salesforce's SOAP API for authentication
2. **Session Token** - Receives a secure session ID
3. **API Calls** - All requests use the session token
4. **No Storage** - Credentials are never saved to disk

### **Security Token**

Your **Security Token** is required unless:
- ✅ Your IP address is whitelisted in Salesforce
- ✅ You're connecting from a trusted network
- ✅ Your org has IP restrictions disabled

**To find your Security Token:**
1. Login to Salesforce
2. Go to **Settings** → **Reset My Security Token**
3. Check your email for the token
4. Append it to your password: `YourPassword + YourToken`

> ⚠️ **Security Warning:** Never share your security token or commit it to version control!

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **❌ "Session Expired" Error**
- **Cause:** Inactive for too long
- **Solution:** Click Logout and login again

#### **❌ "Invalid Username or Password"**
- **Cause:** Wrong credentials or missing security token
- **Solution:** Check your password and append security token

#### **❌ "Access Denied to Report"**
- **Cause:** Insufficient permissions
- **Solution:** Contact your Salesforce admin for access

#### **❌ "Cannot Reach Salesforce"**
- **Cause:** Network issues or wrong custom domain
- **Solution:** Check internet connection and domain spelling

#### **❌ "Excel export not available"**
- **Cause:** `openpyxl` library not installed
- **Solution:** Run `pip install openpyxl` and restart app

#### **❌ Executable won't run / Antivirus blocks**
- **Cause:** PyInstaller executables often trigger false positives
- **Solution:** Add exception in antivirus or build with code signing

---

### **Debug Mode**

Enable debug mode for troubleshooting:

1. Open `main_app.py`
2. Find the `__init__` method (around line 100)
3. Uncomment this line:
```python
   self._enable_debug_mode()
```
4. Restart the app
5. Press `Ctrl+D` to print current state

---

## 📊 Performance Tips

### **For Large Exports (1000+ reports):**

1. **Close other apps** - Free up memory and CPU
2. **Stable internet** - Use wired connection if possible
3. **Batch exports** - Split into multiple smaller exports
4. **Off-peak hours** - Export during low Salesforce usage times
5. **Use CSV format** - Faster than Excel for large datasets

### **For Slow Searches:**

1. **Use specific keywords** - `"Q4 Sales Report"` vs `"Report"`
2. **Check internet speed** - Slow connection = slow API calls
3. **Clear cache** - Restart app to clear old searches
4. **Report count** - Orgs with 10,000+ reports take longer

---

## 🆘 Getting Help

### **Error Messages**

All errors are logged in the **Activity Log** at the bottom of the main window. Copy the error message when reporting issues.

### **Report a Bug**

Include these details:
- Operating System (Windows 10, macOS 14, etc.)
- Python version (`python --version`)
- Error message from Activity Log
- Steps to reproduce

### **Feature Requests**

Open an issue with:
- Clear description of the feature
- Use case / why it's needed
- Expected behavior

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **CustomTkinter** - Modern UI framework
- **Salesforce APIs** - SOAP and REST endpoints
- **Python Community** - Amazing libraries and support

---

## 💡 Tips & Best Practices

### **Organizing Exports**

Create a folder structure for your exports:
```
exports/
├── 2025-01-02_sales_reports.zip
├── 2025-01-02_marketing_reports.zip
└── archive/
    └── 2024-12-15_old_reports.zip
```

### **Backup Strategy**

- ✅ Export critical reports weekly
- ✅ Store ZIPs in cloud storage (Google Drive, OneDrive)
- ✅ Keep last 3 months of exports
- ✅ Document which reports are mission-critical

---

## 🚧 Known Limitations

- **No OAuth2 support** - Uses SOAP login only
- **No report scheduling** - Manual export only
- **No report filtering** - Must select reports manually
- **CSV and Excel only** - No other export formats
- **No email delivery** - Manual download required

---

## 🔮 Roadmap

### **Planned Features:**

- [ ] OAuth2 authentication support
- [ ] Scheduled automatic exports
- [ ] Report filtering by date/owner/type
- [ ] Email delivery of exports
- [ ] Command-line interface (CLI)
- [ ] Docker containerization
- [ ] Web interface version
- [ ] Report preview before export
- [ ] Custom export templates

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 Contact

- **Issues:** [GitHub Issues](https://github.com/yourusername/salesforce-report-exporter/issues)
- **Email:** your.email@example.com
- **Twitter:** @yourusername

---

## ⭐ Show Your Support

If this project helped you, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 📢 Sharing with others

---

**Made with ❤️ for Salesforce Admins and Developers**

*Version 1.0.0 - Released January 2025*