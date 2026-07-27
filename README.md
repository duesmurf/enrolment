# Student Enrolment Agent

An AI-powered agent that connects to your Gmail inbox, retrieves student enrolment documents (Google Sheets / Excel files), processes the data, and automatically sorts students into courses based on their ranked preferences.

## Courses Available

| Course | Max Students |
|--------|-------------|
| Engineering | 5 |
| Design | 5 |
| Sports | 5 |
| IT Systems | 5 |
| Tourism | 5 |

## Quick Start (Git Bash on Windows)

```bash
# 1. Clone the repository
git clone https://github.com/duesmurf/enrolment.git
cd enrolment

# 2. Run the setup script
bash setup.sh

# 3. Place your Google credentials
cp ~/Downloads/credentials.json credentials/

# 4. Test it works
python main.py --demo

# 5. Run the full pipeline
python main.py
```

## Quick Start (Windows CMD / PowerShell)

```cmd
REM 1. Clone the repository
git clone https://github.com/duesmurf/enrolment.git
cd enrolment

REM 2. Run the setup script
setup.bat

REM 3. Place your Google credentials
copy %USERPROFILE%\Downloads\credentials.json credentials\

REM 4. Test it works
python main.py --demo

REM 5. Run the full pipeline
python main.py
```

## Manual Setup

### 1. Create Virtual Environment & Install

**Git Bash:**
```bash
cd /c/Users/YourName/enrolment
python3 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

**CMD/PowerShell:**
```cmd
cd C:\Users\YourName\enrolment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API" and enable it
4. Configure the **OAuth consent screen**:
   - Go to **APIs & Services > OAuth consent screen**
   - Add your email to **Test Users**
5. Create OAuth2 credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth Client ID**
   - Choose **Desktop Application**
   - Download the JSON file
6. Place it in the project:

**Git Bash:**
```bash
cp ~/Downloads/client_secret_*.json credentials/credentials.json
```

**CMD:**
```cmd
copy %USERPROFILE%\Downloads\client_secret_*.json credentials\credentials.json
```

### 3. Configure Environment (Optional)

```bash
cp .env.example .env
```

Edit `.env` to customize:

```env
GMAIL_SEARCH_QUERY=subject:enrolment has:attachment
MAX_STUDENTS_PER_COURSE=5
COURSES=Engineering,Design,Sports,IT Systems,Tourism
```

### 4. Verify Setup

```bash
python main.py --setup
```

This checks Python, packages, credentials, and output directory.

## Usage

### Check Setup
```bash
python main.py --setup
```

### Demo Mode (no Gmail needed)
```bash
python main.py --demo
```

### Full Pipeline (Gmail)
```bash
python main.py
```

On first run, a browser window opens for Google authorization. After that, a token is saved locally.

### Process Local Files
```bash
python main.py --local enrolment.xlsx
python main.py --local file1.csv file2.xlsx
```

### Custom Gmail Search
```bash
python main.py --query "from:registrar@school.edu subject:student enrolment"
```

### Output Format
```bash
python main.py --format xlsx     # Excel only
python main.py --format csv      # CSV only
python main.py --format both     # Both (default)
```

## Expected Input Format

The enrolment spreadsheet should have these columns:

| Name | First Choice | Second Choice | Third Choice | Fourth Choice | Fifth Choice |
|------|-------------|---------------|--------------|---------------|--------------|
| Casey | Engineering | Design | Sports | IT Systems | Tourism |

## Output Format

The generated placement summary:

| S/N | Name | Course |
|-----|------|--------|
| 1 | Casey | Engineering |
| 2 | Jordan | Design |

## Project Structure

```
enrolment/
├── main.py                    # Main entry point & CLI
├── setup.sh                   # Setup script (Git Bash)
├── setup.bat                  # Setup script (Windows CMD)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── .gitignore
├── README.md
├── credentials/               # Google OAuth2 credentials (gitignored)
│   ├── credentials.json       # OAuth2 client secrets (you add this)
│   └── token.json             # Saved auth token (auto-generated)
├── output/                    # Generated placement files
│   ├── placement_summary_*.xlsx
│   ├── placement_summary_*.csv
│   └── detailed_report_*.xlsx
└── src/
    ├── __init__.py
    ├── config.py              # Configuration (auto-resolves paths)
    ├── gmail_client.py        # Gmail API integration
    ├── spreadsheet_processor.py  # Spreadsheet parsing
    ├── allocation_engine.py   # Course allocation logic
    └── output_generator.py    # Output file generation
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate your venv first: `source venv/Scripts/activate` (Git Bash) or `venv\Scripts\activate` (CMD) |
| "Credentials file not found" | Run `python main.py --setup` to see where to place it |
| "Access blocked" in browser | Add your email to Test Users in Google Cloud Console OAuth screen |
| No emails found | Adjust `GMAIL_SEARCH_QUERY` in `.env` or use `--query` flag |
| Path errors on Windows | The code auto-resolves paths - just run from the project folder |

## Security Notes

- OAuth2 tokens are stored locally in `credentials/token.json`
- The agent only requests **read-only** access to Gmail
- Never commit `credentials/` to version control (already in .gitignore)
