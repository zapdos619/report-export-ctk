# 📊 Salesforce Report Exporter

A powerful desktop application for bulk exporting Salesforce reports to CSV format with **no 2,000 row limit**. Built with Python and CustomTkinter for a modern, responsive user experience.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
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
- **Real-time Results** - See matches as you type
- **Organized View** - Reports grouped by folder
- **Cache Management** - Stores last 10 searches for instant access

### 📦 **Export Capabilities**
- **No Row Limit** - Bypass Salesforce's 2,000 row API restriction
- **Batch Export** - Select multiple reports at once
- **ZIP Packaging** - All reports bundled in a single file
- **Progress Tracking** - Real-time progress with ETA and speed
- **Error Recovery** - Retry failed exports automatically

### 🛡️ **Security & Reliability**
- **SOAP Authentication** - No Connected App required
- **Session Management** - Secure token-based authentication
- **Custom Domain Support** - Works with My Domain and custom URLs
- **Sandbox Support** - Connect to sandbox or production orgs
- **Thread-Safe Operations** - Prevents race conditions and crashes

### 🎨 **Modern UI**
- **Dark Mode** - Easy on the eyes
- **Responsive Design** - Adapts to different screen sizes
- **Intuitive Layout** - Clean, organized interface
- **Keyboard Shortcuts** - `Ctrl+E` to export, `ESC` to cancel
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

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
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

---

### **Step 3: Select Reports**

- **Check individual reports** - Click checkbox next to report name
- **Select entire folder** - Click checkbox next to folder name
- **Clear all** - Click "Clear All Selected" button

> 💡 **Tip:** Selected reports appear in the right panel for easy review

---

### **Step 4: Export**

1. Click **Browse** to choose save location
2. (Optional) Edit the ZIP filename
3. Click **🚀 Export Reports** or press `Ctrl+E`
4. Wait for progress to complete
5. Open the exported ZIP file

> 💡 **Tip:** Press `ESC` to cancel an export in progress

---

## 🎯 Advanced Usage

### **Keyboard Shortcuts**

| Shortcut | Action |
|----------|--------|
| `Enter` | Execute search / Login |
| `Ctrl+E` | Start export |
| `ESC` | Cancel current operation |
| `Ctrl+D` | Print debug state (debug mode) |

---

### **Search Tips**

- **Broad keywords** - `"Sales"` finds all sales-related reports
- **Specific names** - `"Q4 Revenue Report"` finds exact matches
- **Partial matches** - `"Rev"` finds "Revenue", "Review", etc.
- **Case insensitive** - `"SALES"` and `"sales"` work the same

---

### **Export Options**

#### **Concurrent Downloads**
The app downloads up to 10 reports simultaneously for faster exports:
- Small exports (1-10 reports): ~5-10 seconds
- Medium exports (50 reports): ~30-60 seconds
- Large exports (500+ reports): ~3-5 minutes

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
└── .gitignore            # Git ignore rules
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

#### **❌ "Not Responding" / UI Freezes**
- **Cause:** Running on old version without threading fixes
- **Solution:** Update to latest version (v2.0.0+)

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

#### **❌ Minimize Button Doesn't Work**
- **Cause:** Running old version
- **Solution:** Update to v2.0.0+ (has minimize fix)

---

### **Debug Mode**

Enable debug mode for troubleshooting:

1. Open `main_app.py`
2. Find the `__init__` method
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

## 🔄 Changelog

### **v2.0.0** (Latest) - 2025-01-30
- ✅ **Fixed:** "Not Responding" freeze during search
- ✅ **Fixed:** Minimize button now works
- ✅ **Added:** Virtual scrolling for 10,000+ reports
- ✅ **Added:** Search result caching
- ✅ **Added:** Concurrent downloads (10x faster)
- ✅ **Added:** Real-time progress with ETA
- ✅ **Improved:** Thread safety and error handling
- ✅ **Improved:** State management (atomic operations)

### **v1.0.0** - 2024-12-15
- Initial release
- Basic search and export functionality
- SOAP authentication
- Single-threaded downloads

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
├── 2025-01-30_sales_reports.zip
├── 2025-01-30_marketing_reports.zip
└── archive/
    └── 2024-12-15_old_reports.zip
```

### **Scheduling Exports**

While the app doesn't have built-in scheduling, you can:
1. Export reports manually on a regular schedule
2. Use Windows Task Scheduler / cron to run exports
3. Build a script wrapper around the exporter module

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
- **No custom formats** - CSV export only
- **No email delivery** - Manual download required

---

## 🔮 Roadmap

### **Planned Features:**

- [ ] OAuth2 authentication support
- [ ] Scheduled automatic exports
- [ ] Excel (XLSX) export format
- [ ] Report filtering by date/owner
- [ ] Email delivery of exports
- [ ] Command-line interface (CLI)
- [ ] Docker containerization
- [ ] Web interface version

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

*Last Updated: January 30, 2025*