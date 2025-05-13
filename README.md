# Lonely Web Project

## Overview

Lonely Web is a project designed to discover and showcase obscure YouTube videos. It consists of two main components:
1.  A **Go-based web server** that displays a random YouTube video from a curated database. It features continuous auto-play to the next video and a manual button to load a new one.
2.  A suite of **Python scripts** for collecting YouTube video URLs and their metadata, storing them in an SQLite database. Collection can be done via the YouTube Data API or, experimentally, through web scraping.

The Go web server is designed to be a single, self-contained binary, embedding both its HTML templates and the video database content for maximum portability.

## Features

### Go Web Server (`go_frontend`)
- Displays one random YouTube video at a time.
- Automatically plays the next random video when the current one finishes.
- "Show New Video" button to manually load a different random video.
- Server port is configurable (defaults to `8080`, can be set via `LONELYWEB_SERVER_PORT` environment variable).
- Embeds HTML templates directly into the binary.
- Embeds the SQLite video database content directly into the binary.
- Client-side JavaScript interaction using the YouTube IFrame Player API for player control.

### Python YouTube Collector (`youtube_collector`)
- **Database Initialization**: Script to set up the SQLite database (`youtube_videos.db`).
- **Low-View Video Collection (API)**: Collects a specified number of YouTube video URLs that have less than 50 views using the YouTube Data API.

## Directory Structure

```
lonelyweb/
├── go_frontend/            # Go web server application
│   ├── main.go             # Main Go application logic
│   ├── database.go         # Go database interaction (in-memory with embedded data)
│   ├── templates/          # HTML templates (embedded at compile time)
│   │   └── index.html
│   ├── data/               # Directory for embedded data source
│   │   └── embedded_data.sql # SQL dump of the video database (embedded at compile time)
│   ├── go.mod              # Go module definition
│   └── go.sum              # Go module checksums
├── youtube_collector/      # Python scripts for collecting video data
│   ├── main.py             # Script to collect low-view videos via YouTube API
│   ├── db_setup.py         # Script to initialize the SQLite database
│   ├── requirements.txt    # Python dependencies (can be used with pip or uv)
│   └── data/               # Directory where the live SQLite database is stored
│       └── youtube_videos.db # The primary SQLite database populated by collector scripts
└── legacy/                 # Legacy files
```

## Setup

### Prerequisites
- **Go**: Version 1.16 or higher (for the `embed` package).
- **Python**: Version 3.7 or higher.
- **SQLite3 CLI**: The command-line tool for SQLite. This is needed to dump the database for embedding in the Go application.
- **`uv` (Optional but Recommended for Python)**: For Python environment and package management. If not using `uv`, `pip` can be used.

### 1. Python YouTube Collector (`youtube_collector`)

Navigate to the `youtube_collector` directory:
```bash
cd lonelyweb/youtube_collector
```

**a. Create a Python Virtual Environment (Recommended)**
Using `uv`:
```bash
uv venv
source .venv/bin/activate  # On Linux/macOS
# .\.venv\Scripts\Activate.ps1 # On Windows PowerShell
```
Or using standard `venv`:
```bash
python3 -m venv .venv
source .venv/bin/activate # On Linux/macOS
# .\.venv\Scripts\Activate.ps1 # On Windows PowerShell
```

**b. Install Python Dependencies**
Ensure your `youtube_collector/requirements.txt` file contains:
```txt
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
requests
beautifulsoup4
lxml
```
Then install them:
```bash
uv pip install -r requirements.txt
# Or, if not using uv:
# pip install -r requirements.txt
```

**c. YouTube Data API Key**
For scripts that use the YouTube Data API (`main.py`, `import_legacy_urls.py`), you need a YouTube Data API v3 key:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the "YouTube Data API v3" for your project.
4. Create credentials (API key).
5. **Important**: Secure your API key. Do not commit it to your repository. Pass it as a command-line argument as required by the scripts.

### 2. Go Web Server (`go_frontend`)

Navigate to the `go_frontend` directory:
```bash
cd lonelyweb/go_frontend # Or ../go_frontend if coming from youtube_collector
```

**a. Get Go Dependencies**
This will fetch `github.com/spf13/viper` (for configuration) and `github.com/mattn/go-sqlite3` (SQLite driver).
```bash
go get github.com/spf13/viper
go get github.com/mattn/go-sqlite3
go mod tidy
```

## Usage

### 1. Populate the Video Database (`youtube_collector`)

First, ensure your Python environment (e.g., `.venv`) is activated. From within the `lonelyweb/youtube_collector` directory:

**a. Initialize the Database**
```bash
python db_setup.py
```
This creates `youtube_collector/data/youtube_videos.db` if it doesn't exist, along with the necessary `videos` table.

**b. Collect Videos**
You have several options to populate the database:

*   **Collect Low-View Videos (API):**
    ```bash
    python main.py YOUR_YOUTUBE_API_KEY -n <number_of_videos>
    # Example: python main.py YOUR_API_KEY -n 1000
    ```
    Replace `YOUR_YOUTUBE_API_KEY` with your actual key. `<number_of_videos>` is optional and defaults to 50,000.

### 2. Prepare Data for the Go Web Server

The Go web server uses an *embedded* version of the database. After populating or updating `lonelyweb/youtube_collector/data/youtube_videos.db`, you need to create an SQL dump for the Go application.

From the **root directory of the `lonelyweb` project**, run:
```bash
sqlite3 youtube_collector/data/youtube_videos.db .dump > go_frontend/data/embedded_data.sql
```
This command updates the `embedded_data.sql` file that will be compiled into the Go binary.

**Important:** You must re-run this SQL dump command and then recompile the Go application whenever you want the web server to use updated video data.

### 3. Run the Go Web Server (`go_frontend`)

Navigate to the `lonelyweb/go_frontend` directory:
```bash
cd go_frontend # If not already there
```

**a. Compile and Run**
```bash
go run .
```
Alternatively, to build a standalone binary (e.g., `lonelyweb_app`):
```bash
go build -o lonelyweb_app .
# Then run the binary:
# ./lonelyweb_app
```

**b. Configuration**
- **Port:** The server defaults to port `8080`. You can change this by setting the `LONELYWEB_SERVER_PORT` environment variable:
  ```bash
  LONELYWEB_SERVER_PORT=9090 go run .
  # Or for the compiled binary:
  # LONELYWEB_SERVER_PORT=9090 ./lonelyweb_app
  ```

**c. Accessing the Web Interface**
Open your web browser and go to `http://localhost:<port>` (e.g., `http://localhost:8080` if using the default port).

The page will display a random video. When the video ends, another random video should automatically load and play. You can also click the "Show New Video" button to manually load a different video.

## Development Notes

- **Updating Embedded Assets**: Remember that both the video database content (`go_frontend/data/embedded_data.sql`) and HTML templates (`go_frontend/templates/*.html`) are embedded into the Go binary at compile time. If you make changes to these source files (or update the source database for `embedded_data.sql`), you **must recompile** the Go application for the changes to take effect.
- **Scraping Fragility**: The web scraping script (`scrape_legacy_urls.py`) is highly dependent on the HTML structure of YouTube pages and is provided as an experimental alternative. It may break frequently if YouTube updates its website. Using the API-based methods is generally more reliable.
- **API Quotas**: Be mindful of YouTube Data API quotas. Extensive use of the API-based collector scripts can consume your daily quota quickly.

## Contributing
Contributions are welcome! Please feel free to submit pull requests or open issues.

## License
This project is released under the MIT License.
