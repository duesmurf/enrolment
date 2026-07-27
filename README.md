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

## How It Works

1. **Gmail Retrieval** - Connects to Gmail via OAuth2, searches for emails with spreadsheet attachments matching your query
2. **Document Processing** - Parses downloaded `.xlsx`, `.xls`, or `.csv` files to extract student names and course preferences
3. **Course Allocation** - Assigns each student to a course using a preference-based algorithm (first choice prioritized, falls back to next choices if a course is full)
4. **Output Generation** - Produces a placement summary file (`S/N`, `Name`, `Course`) in Excel and/or CSV format

## Expected Input Format

The enrolment spreadsheet should have the following columns:

| Name | First Choice | Second Choice | Third Choice | Fourth Choice | Fifth Choice |
|------|-------------|---------------|--------------|---------------|--------------|
| Casey | Engineering | Design | Sports | IT Systems | Tourism |

## Output Format

The generated placement summary:

| S/N | Name | Course |
|-----|------|--------|
| 1 | Casey | Engineering |
| 2 | Jordan | Design |

## Setup

### Prerequisites

- Python 3.10+
- A Google Cloud project with Gmail API enabled
- OAuth2 credentials (Desktop application type)

### 1. Clone and Install Dependencies

```bash
cd student-enrolment-agent
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API" and enable it
4. Create OAuth2 credentials:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth Client ID**
   - Choose **Desktop Application**
   - Download the JSON file
5. Save the credentials file as `credentials/credentials.json`

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to customize:

```env
# Path to your OAuth2 credentials JSON file
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json

# Gmail search query to find enrolment emails
GMAIL_SEARCH_QUERY=subject:enrolment has:attachment

# Maximum number of students per course
MAX_STUDENTS_PER_COURSE=5

# Output directory for generated placement files
OUTPUT_DIR=output

# Available courses (comma-separated)
COURSES=Engineering,Design,Sports,IT Systems,Tourism
```

### 4. First Run (Authentication)

On the first run, a browser window will open asking you to authorize Gmail access. After authorization, a token is saved locally for future sessions.

## Usage

### Full Pipeline (Gmail Mode)

Fetch enrolment files from Gmail, process them, and generate output:

```bash
python main.py
```

With a custom Gmail search query:

```bash
python main.py --query "from:registrar@school.edu subject:student enrolment"
```

### Local File Mode

Process spreadsheet files directly (no Gmail needed):

```bash
python main.py --local enrolment.xlsx
python main.py --local file1.csv file2.xlsx
```

### Demo Mode

Run with built-in sample data to verify the system works:

```bash
python main.py --demo
```

### Output Format Options

```bash
python main.py --format xlsx     # Excel only
python main.py --format csv      # CSV only
python main.py --format both     # Both (default)
```

## Project Structure

```
student-enrolment-agent/
├── main.py                    # Main entry point & CLI
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── README.md                  # This file
├── credentials/               # Google OAuth2 credentials (gitignored)
│   ├── credentials.json       # OAuth2 client secrets
│   └── token.json             # Saved auth token (auto-generated)
├── output/                    # Generated placement files
│   ├── placement_summary_*.xlsx
│   ├── placement_summary_*.csv
│   └── detailed_report_*.xlsx
└── src/
    ├── __init__.py
    ├── config.py              # Configuration management
    ├── gmail_client.py        # Gmail API integration
    ├── spreadsheet_processor.py  # Spreadsheet parsing
    ├── allocation_engine.py   # Course allocation logic
    └── output_generator.py    # Output file generation
```

## Allocation Algorithm

The agent uses a **first-come-first-served preference-based** allocation:

1. Students are processed in the order they appear in the spreadsheet
2. For each student, their **1st choice** is tried first
3. If that course is full (5 students), the **2nd choice** is tried, and so on
4. If all preferred courses are full, the student is marked as **unplaced**
5. The detailed report includes an "Unplaced" sheet listing these students

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Credentials file not found" | Download OAuth2 credentials from Google Cloud Console and save to `credentials/credentials.json` |
| "No enrolment files found" | Adjust the `GMAIL_SEARCH_QUERY` in `.env` to match your emails |
| "Could not find a 'Name' column" | Ensure your spreadsheet has a column named "Name", "Student Name", or "Student" |
| "Could not find course choice columns" | Ensure columns contain "Choice" in their name (e.g., "First Choice") |
| Authentication errors | Delete `credentials/token.json` and re-run to re-authenticate |

## Security Notes

- OAuth2 tokens are stored locally in `credentials/token.json`
- The agent only requests **read-only** access to Gmail (`gmail.readonly` scope)
- Never commit `credentials/` to version control
- Add `credentials/` and `output/` to your `.gitignore`
