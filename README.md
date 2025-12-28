# Chronicler

A GitHub organization repository monitor that tracks changes in public repositories.

## Overview

Chronicler monitors the `LookAtWhatAiCanDo` organization on GitHub, tracking all public repositories and their metadata. The monitoring script runs automatically every 24 hours via GitHub Actions.

## Features

- 📊 Fetches all public repositories from the organization
- 🔄 Tracks repository metadata (stars, forks, languages, updates)
- 📸 Creates timestamped snapshots of repository states
- ⏰ Runs automatically every 24 hours
- 🚀 Can be triggered manually via GitHub Actions

## Components

### `monitor_repos.py`

The main Python script that:
- Connects to the GitHub API
- Fetches all public repositories for the organization
- Extracts relevant metadata (name, description, stars, forks, etc.)
- Saves snapshots to JSON files
- Displays a summary of the repositories

### GitHub Action (`.github/workflows/monitor-repos.yml`)

Automated workflow that:
- Runs daily at midnight UTC
- Can be triggered manually via workflow_dispatch
- Uploads snapshots as artifacts (retained for 90 days)

## Usage

### Manual Execution

To run the script locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (optional but recommended)
export GITHUB_TOKEN=your_github_token
export GITHUB_ORG=LookAtWhatAiCanDo

# Run the monitor
python monitor_repos.py
```

### GitHub Actions

The workflow runs automatically, but you can also:
1. Go to the "Actions" tab in the repository
2. Select "Monitor Organization Repositories"
3. Click "Run workflow" to trigger manually

## Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (optional, but recommended to avoid rate limits)
- `GITHUB_ORG`: Organization name to monitor (defaults to `LookAtWhatAiCanDo`)

## Output

The script generates:
- Console summary showing recently updated repositories
- JSON snapshots in the `snapshots/` directory with format: `{org}_{timestamp}.json`

Each snapshot contains:
- Organization name
- Timestamp
- Total repository count
- Detailed information for each repository

## Future Enhancements

The functionality will grow to include:
- Change detection between snapshots
- Notifications for new repositories
- Tracking repository activity trends
- Generating reports and visualizations

## License

See [LICENSE](LICENSE) file for details.