#!/usr/bin/env python3
"""
Repository Monitor Script

This script monitors a GitHub organization for changes in public repositories.
It fetches the list of public repositories and can be extended to track changes over time.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_github_token() -> Optional[str]:
    """
    Get GitHub token from environment variable.
    
    Returns:
        GitHub token or None if not found
    """
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.warning("GITHUB_TOKEN not found in environment variables")
    return token


def get_requests_module():
    """
    Import and return the requests module.
    
    Returns:
        requests module
    """
    try:
        import requests
        return requests
    except ImportError:
        logger.error("requests library not installed. Please install requirements.txt")
        sys.exit(1)


def fetch_org_repos(org_name: str, token: Optional[str] = None) -> List[Dict]:
    """
    Fetch public repositories for a GitHub organization.
    
    Args:
        org_name: Name of the GitHub organization
        token: Optional GitHub token for authentication
        
    Returns:
        List of repository information dictionaries
    """
    requests = get_requests_module()
    
    url = f"https://api.github.com/orgs/{org_name}/repos"
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    params = {
        'type': 'public',
        'per_page': 100,
        'sort': 'updated',
        'direction': 'desc'
    }
    
    all_repos = []
    page = 1
    
    while True:
        params['page'] = page
        logger.info(f"Fetching page {page} of repositories...")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # Check for rate limit
                rate_limit_remaining = e.response.headers.get('X-RateLimit-Remaining', 'unknown')
                rate_limit_reset = e.response.headers.get('X-RateLimit-Reset', 'unknown')
                logger.error(f"GitHub API rate limit exceeded or forbidden access.")
                logger.error(f"Rate limit remaining: {rate_limit_remaining}, Reset time: {rate_limit_reset}")
                logger.error("Consider setting GITHUB_TOKEN environment variable to increase rate limits.")
            logger.error(f"Error fetching repositories: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories: {e}")
            raise
        
        repos = response.json()
        if not repos:
            break
            
        all_repos.extend(repos)
        
        # Check if there are more pages
        if 'Link' not in response.headers or 'rel="next"' not in response.headers['Link']:
            break
            
        page += 1
    
    logger.info(f"Found {len(all_repos)} public repositories")
    return all_repos


def fetch_latest_commit(repo_full_name: str, token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch the latest commit information for a repository.
    
    Args:
        repo_full_name: Full name of the repository (e.g., 'owner/repo')
        token: Optional GitHub token for authentication
        
    Returns:
        Dictionary with commit information or None if failed
    """
    requests = get_requests_module()
    
    url = f"https://api.github.com/repos/{repo_full_name}/commits"
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    params = {
        'per_page': 1,  # Only get the latest commit
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        commits = response.json()
        
        if commits:
            commit = commits[0]
            return {
                'sha': commit['sha'],
                'author': commit['commit']['author']['name'],
                'date': commit['commit']['author']['date'],
                'message': commit['commit']['message'],
            }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching latest commit for {repo_full_name}: {e}")
    
    return None


def fetch_commit_comparison(repo_full_name: str, base_sha: str, head_sha: str, 
                            token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch comparison between two commits.
    
    Args:
        repo_full_name: Full name of the repository (e.g., 'owner/repo')
        base_sha: Base commit SHA
        head_sha: Head commit SHA
        token: Optional GitHub token for authentication
        
    Returns:
        Dictionary with comparison information or None if failed
    """
    requests = get_requests_module()
    
    url = f"https://api.github.com/repos/{repo_full_name}/compare/{base_sha}...{head_sha}"
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        comparison = response.json()
        
        return {
            'commits_count': len(comparison.get('commits', [])),
            'files_changed': len(comparison.get('files', [])),
            'additions': comparison.get('total_additions', 0),
            'deletions': comparison.get('total_deletions', 0),
            'commits': [
                {
                    'sha': c['sha'][:7],
                    'author': c['commit']['author']['name'],
                    'message': c['commit']['message'].split('\n')[0][:80],  # First line, truncated
                    'date': c['commit']['author']['date'],
                }
                for c in comparison.get('commits', [])
            ]
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching commit comparison for {repo_full_name}: {e}")
    
    return None


def extract_repo_info(repos: List[Dict], token: Optional[str] = None) -> List[Dict]:
    """
    Extract relevant information from repository data.
    
    Args:
        repos: List of repository data from GitHub API
        token: Optional GitHub token for authentication
        
    Returns:
        List of simplified repository information
    """
    extracted = []
    for repo in repos:
        info = {
            'name': repo['name'],
            'full_name': repo['full_name'],
            'description': repo.get('description', 'No description'),
            'url': repo['html_url'],
            'created_at': repo['created_at'],
            'updated_at': repo['updated_at'],
            'pushed_at': repo.get('pushed_at'),
            'language': repo.get('language'),
            'stars': repo['stargazers_count'],
            'forks': repo['forks_count'],
            'open_issues': repo['open_issues_count'],
            'is_archived': repo['archived'],
            'is_fork': repo['fork'],
        }
        
        # Fetch latest commit information
        latest_commit = fetch_latest_commit(repo['full_name'], token)
        if latest_commit:
            info['latest_commit'] = latest_commit
        
        extracted.append(info)
    
    return extracted


def save_snapshot(org_name: str, repos_info: List[Dict]) -> str:
    """
    Save a snapshot of repository information to a JSON file.
    
    Args:
        org_name: Name of the organization
        repos_info: List of repository information
        
    Returns:
        Path to the saved snapshot file
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    snapshot = {
        'organization': org_name,
        'timestamp': timestamp,
        'repository_count': len(repos_info),
        'repositories': repos_info
    }
    
    filename = f"snapshots/{org_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('snapshots', exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    logger.info(f"Snapshot saved to {filename}")
    return filename


def load_latest_snapshot(org_name: str) -> Optional[Dict]:
    """
    Load the most recent snapshot for an organization.
    
    Args:
        org_name: Name of the organization
        
    Returns:
        Snapshot data or None if no previous snapshot exists
    """
    snapshots_dir = 'snapshots'
    if not os.path.exists(snapshots_dir):
        return None
    
    # Find all snapshot files for this organization
    snapshot_files = [
        f for f in os.listdir(snapshots_dir)
        if f.startswith(f"{org_name}_") and f.endswith('.json')
    ]
    
    if not snapshot_files:
        return None
    
    # Sort by filename (which includes timestamp) and get the most recent
    snapshot_files.sort(reverse=True)
    latest_file = os.path.join(snapshots_dir, snapshot_files[0])
    
    try:
        with open(latest_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading previous snapshot {latest_file}: {e}")
        return None


def detect_changes(current_repos: List[Dict], previous_snapshot: Optional[Dict],
                  token: Optional[str] = None) -> Dict[str, Dict]:
    """
    Detect changes between current and previous repository snapshots.
    
    Args:
        current_repos: Current repository information
        previous_snapshot: Previous snapshot data
        token: Optional GitHub token for authentication
        
    Returns:
        Dictionary mapping repo names to change information
    """
    changes = {}
    
    if not previous_snapshot:
        logger.info("No previous snapshot found - all repositories are new")
        return changes
    
    # Create a mapping of previous repositories by name
    previous_repos = {
        repo['name']: repo
        for repo in previous_snapshot.get('repositories', [])
    }
    
    for current_repo in current_repos:
        repo_name = current_repo['name']
        current_commit = current_repo.get('latest_commit', {})
        
        if not current_commit:
            continue
        
        # Check if repo existed in previous snapshot
        if repo_name not in previous_repos:
            changes[repo_name] = {
                'type': 'new_repository',
                'latest_commit': current_commit,
            }
            continue
        
        previous_repo = previous_repos[repo_name]
        previous_commit = previous_repo.get('latest_commit', {})
        
        if not previous_commit:
            continue
        
        # Check if commit has changed
        if current_commit.get('sha') != previous_commit.get('sha'):
            # Fetch detailed comparison
            comparison = fetch_commit_comparison(
                current_repo['full_name'],
                previous_commit['sha'],
                current_commit['sha'],
                token
            )
            
            changes[repo_name] = {
                'type': 'updated',
                'previous_commit': previous_commit,
                'latest_commit': current_commit,
                'comparison': comparison,
            }
    
    return changes


def display_summary(org_name: str, repos_info: List[Dict], changes: Optional[Dict[str, Dict]] = None) -> None:
    """
    Display a summary of the repository information.
    
    Args:
        org_name: Name of the organization
        repos_info: List of repository information
        changes: Optional dictionary of detected changes
    """
    print(f"\n{'='*80}")
    print(f"Organization: {org_name}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total public repositories: {len(repos_info)}")
    print(f"{'='*80}\n")
    
    # Display changes if available
    if changes:
        new_repos = [name for name, change in changes.items() if change['type'] == 'new_repository']
        updated_repos = [name for name, change in changes.items() if change['type'] == 'updated']
        
        if new_repos or updated_repos:
            print("=" * 80)
            print("CHANGES SINCE LAST CHECK")
            print("=" * 80)
            
            if new_repos:
                print(f"\n🆕 New repositories ({len(new_repos)}):")
                for repo_name in new_repos[:5]:  # Show first 5
                    change = changes[repo_name]
                    commit = change.get('latest_commit', {})
                    print(f"  • {repo_name}")
                    if commit:
                        print(f"    Latest commit: {commit.get('sha', 'N/A')[:7]}")
                        print(f"    Message: {commit.get('message', 'N/A').split('\n')[0][:60]}")
                if len(new_repos) > 5:
                    print(f"  ... and {len(new_repos) - 5} more")
            
            if updated_repos:
                print(f"\n📝 Updated repositories ({len(updated_repos)}):")
                for repo_name in updated_repos[:10]:  # Show first 10
                    change = changes[repo_name]
                    comparison = change.get('comparison', {})
                    latest = change.get('latest_commit', {})
                    
                    print(f"\n  • {repo_name}")
                    print(f"    Latest commit: {latest.get('sha', 'N/A')[:7]} by {latest.get('author', 'N/A')}")
                    print(f"    Message: {latest.get('message', 'N/A').split('\n')[0][:70]}")
                    
                    if comparison:
                        commits_count = comparison.get('commits_count', 0)
                        files_changed = comparison.get('files_changed', 0)
                        print(f"    Changes: {commits_count} commit(s), {files_changed} file(s) changed")
                        
                        # Show recent commits
                        commits = comparison.get('commits', [])
                        if commits and len(commits) <= 3:
                            print(f"    Commits:")
                            for commit in commits:
                                print(f"      - {commit['sha']}: {commit['message']}")
                
                if len(updated_repos) > 10:
                    print(f"  ... and {len(updated_repos) - 10} more")
            
            print(f"\n{'='*80}\n")
    
    if repos_info:
        print("Recently updated repositories:")
        print(f"{'Repository':<40} {'Updated':<20} {'Stars':<8} {'Language':<15}")
        print(f"{'-'*80}")
        
        for repo in repos_info[:10]:  # Show top 10 most recently updated
            name = repo.get('name', 'N/A')[:38] + '..' if len(repo.get('name', '')) > 38 else repo.get('name', 'N/A')
            updated = repo.get('updated_at', 'N/A')[:10] if repo.get('updated_at') else 'N/A'
            stars = str(repo.get('stars', 0))
            language = (repo.get('language') or 'N/A')[:13]
            print(f"{name:<40} {updated:<20} {stars:<8} {language:<15}")
    
    print(f"\n{'='*80}\n")


def main():
    """
    Main function to monitor organization repositories.
    """
    # Default organization to monitor
    org_name = os.environ.get('GITHUB_ORG', 'LookAtWhatAiCanDo')
    
    logger.info(f"Starting repository monitor for organization: {org_name}")
    
    # Get GitHub token (optional but recommended to avoid rate limits)
    token = get_github_token()
    
    try:
        # Load previous snapshot for comparison
        previous_snapshot = load_latest_snapshot(org_name)
        if previous_snapshot:
            logger.info(f"Loaded previous snapshot from {previous_snapshot.get('timestamp')}")
        else:
            logger.info("No previous snapshot found - this is the first run")
        
        # Fetch repositories
        repos = fetch_org_repos(org_name, token)
        
        # Extract relevant information (including latest commits)
        repos_info = extract_repo_info(repos, token)
        
        # Detect changes since last snapshot
        changes = detect_changes(repos_info, previous_snapshot, token)
        if changes:
            logger.info(f"Detected changes in {len(changes)} repositories")
        
        # Display summary with changes
        display_summary(org_name, repos_info, changes)
        
        # Save snapshot
        save_snapshot(org_name, repos_info)
        
        logger.info("Repository monitoring completed successfully")
        
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
