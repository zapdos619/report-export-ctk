# 📊 Salesforce Report Exporter

A powerful desktop application to bulk export Salesforce reports, bypassing the 2,000 row API limit. Built with Python and CustomTkinter for a modern, user-friendly experience.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

### Core Functionality

- 🚀 **Bulk Export** - Export multiple reports simultaneously
- 📁 **Folder-Based Selection** - Select entire folders or individual reports
- 🔍 **Smart Search** - Instantly find reports across all folders
- 📦 **ZIP Packaging** - All exports bundled in a single compressed file
- ♾️ **Unlimited Rows** - Bypasses Salesforce's 2,000 row API limitation

### User Experience

- 🎨 **Modern Dark UI** - Clean, professional interface built with CustomTkinter
- 📊 **Real-Time Progress** - Live progress bar and detailed activity logs
- 🌳 **Tree View Navigation** - Intuitive folder/report hierarchy
- 🎯 **Dual-Panel Selection** - Available items on left, selected items on right
- ⚡ **Fast Performance** - Multi-threaded export with retry logic

### Technical Features

- 🔐 **Universal Authentication** - Works with any Salesforce org (no Connected App needed)
- 🌍 **Multi-Environment Support** - Production, Sandbox, and Custom Domains
- 🤖 **Dynamic API Detection** - Automatically uses latest org API version
- 🧹 **Auto CSV Cleaning** - Removes Salesforce metadata footers
- 🛡️ **Error Resilience** - Continues exporting even if individual reports fail

---

## 🖼️ Screenshots

### Main Application Window

- Tree view with folder/report hierarchy
- Dual-panel selection interface
- Real-time progress tracking

### Login Window

- Production/Sandbox/Custom Domain support
- Simple credential entry
- Secure authentication

---

## 📋 Requirements

- **Python 3.10 or higher**
- **Operating System:** Windows 10/11, macOS 10.14+, or Linux
- **Salesforce Account** with report access permissions
- **Internet Connection** for API calls

---

## 🚀 Installation

### 1. Clone or Download Repository

```bash
git clone https://github.com/yourusername/salesforce-report-exporter.git
cd salesforce-report-exporter
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Application

```bash
python main_app.py
```

---

## 📖 How to Use

### Step 1: Login to Salesforce

1. Launch the application
2. Click **"Login to Salesforce"**
3. Select environment (Production/Sandbox) or enter Custom Domain
4. Enter credentials:
   - Username (email)
   - Password
   - Security Token (optional if IP whitelisted)
5. Click **"Login to Salesforce"**

### Step 2: Browse and Select Reports

1. After login, folders and reports load automatically
2. Use the **search box** to filter reports
3. Click **folder checkboxes** to select all reports in a folder
4. Or click **individual report checkboxes** for specific reports
5. Selected reports appear in the **right panel**

### Step 3: Export Reports

1. Click **"Browse..."** to choose save location
2. Edit the ZIP filename if desired (auto-generated timestamp)
3. Click **"🚀 Export Reports"**
4. Monitor progress in real-time
5. View detailed logs in the Activity Log section

### Step 4: Review Results

- Export completes with success/failure summary
- ZIP file contains all exported CSVs
- `_EXPORT_SUMMARY.txt` included with details
- Failed reports listed with error messages

---

## 🔑 Authentication Methods

### Option 1: Security Token (Most Common)

```
Username: your.email@company.com
Password: YourPassword
Security Token: YourSecurityToken
```

**Note:** Token is appended to password automatically

### Option 2: IP Whitelisting

If your IP is whitelisted in Salesforce:

```
Username: your.email@company.com
Password: YourPassword
Security Token: [Leave blank]
```

### Environments

- **Production:** `login.salesforce.com`
- **Sandbox:** `test.salesforce.com`
- **Custom Domain:** `yourcompany.my.salesforce.com`

---

## 🛠️ Technical Architecture

### Project Structure

```
salesforce-report-exporter/
│
├── main_app.py           # Main application window & UI logic
├── login_window.py       # Login dialog window
├── salesforce_auth.py    # SOAP authentication handler
├── exporter.py           # Export engine & Salesforce API client
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

### Key Technologies

- **CustomTkinter** - Modern UI framework for Python
- **Requests** - HTTP library for API calls
- **Threading** - Async operations for non-blocking UI
- **Queue** - Thread-safe UI updates
- **SOAP API** - Authentication (no OAuth required)
- **REST API** - Report metadata retrieval
- **Export URLs** - Direct CSV download (bypasses row limits)

### API Strategy

1. **SOAP Login** - Universal authentication method
2. **REST API** - List folders and reports with metadata
3. **SOQL Queries** - Get reports by folder (accurate filtering)
4. **UI Export URLs** - Download actual CSV data (unlimited rows)

---

## ⚙️ Configuration

### Rate Limiting

Default delay between exports: `0.5 seconds`

To modify, edit `exporter.py`:

```python
delay_between_reports: float = 1.0  # Increase for safer rate limiting
```

### API Version

Automatically detected from org. To force a specific version:

```python
exporter = SalesforceReportExporter(
    session_id,
    instance_url,
    api_version="61.0"  # Force specific version
)
```

### Window Size

Default: `1200x800` pixels

To modify, edit `main_app.py`:

```python
self.geometry("1400x900")  # Adjust as needed
```

---

## 🐛 Troubleshooting

### Issue: "Session expired or invalid"

**Solution:** Your session timed out. Logout and login again.

### Issue: "Access denied to this report"

**Solution:** Your user doesn't have permission to access that report.

### Issue: "No reports found in folder"

**Solution:**

- Folder might be empty
- Reports might be in sub-folders (not yet supported)
- Check folder permissions

### Issue: Export fails with timeout

**Solution:**

- Large reports may take time
- Check internet connection
- Increase timeout in `retry_request()` function

### Issue: CSV has wrong data

**Solution:**

- Report might have filters applied in Salesforce
- Verify report runs correctly in Salesforce UI first

### Issue: Login fails

**Solution:**

- Verify credentials are correct
- Ensure security token is current (resets on password change)
- Check if IP needs whitelisting
- Try Sandbox if Production fails (confirms credentials work)

---

## 📊 Export Format

### ZIP Contents

```
salesforce_reports_20251126_1430.zip
│
├── _EXPORT_SUMMARY.txt          # Export statistics & errors
├── Account_Report.csv           # Individual report CSVs
├── Opportunity_Pipeline.csv
├── Sales_Forecast_Q4.csv
└── ...
```

### CSV Format

- **UTF-8 Encoding**
- **Comma-separated** values
- **Headers included** in first row
- **Salesforce metadata footer removed** automatically
- **Duplicate filenames** handled with numbering (`Report_1.csv`, `Report_2.csv`)

---

## 🔒 Security Notes

- ✅ Credentials never stored or logged
- ✅ Session tokens kept in memory only
- ✅ HTTPS for all API communication
- ✅ No third-party analytics or tracking
- ⚠️ Exported ZIPs contain raw data - secure appropriately
- ⚠️ Use dedicated API user for automation (recommended)

---

## 🚧 Known Limitations

1. **Sub-folders not supported** - Only top-level folders shown
2. **Dashboard exports not supported** - Reports only
3. **Matrix reports** - May require manual formatting
4. **Joined reports** - Exported as-is (may need processing)
5. **Very large orgs** - Initial load may take time (100+ folders)

---

## 🗺️ Roadmap

### Planned Features

- [ ] Dashboard export support
- [ ] Sub-folder navigation
- [ ] Scheduled/automated exports
- [ ] Excel format export option
- [ ] Report metadata backup (formulas, filters)
- [ ] Incremental exports (only changed reports)
- [ ] Cloud storage integration (S3, Google Drive)
- [ ] Email notifications on completion

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest

# Format code
black .

# Lint
flake8 .
```

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **CustomTkinter** - Modern UI framework
- **Salesforce API Documentation** - Comprehensive API guides
- **Python Community** - Amazing libraries and support

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/salesforce-report-exporter/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/salesforce-report-exporter/discussions)
- **Email:** your.email@example.com

---

## ⭐ Show Your Support

If this project helped you, please give it a ⭐️!

---

## 📚 Additional Resources

- [Salesforce API Documentation](https://developer.salesforce.com/docs/apis)
- [CustomTkinter Documentation](https://customtkinter.tomschimansky.com/)
- [Python Threading Guide](https://docs.python.org/3/library/threading.html)

---

**Built with ❤️ by Nahid Hasan**

_Making Salesforce data exports simple and efficient_
