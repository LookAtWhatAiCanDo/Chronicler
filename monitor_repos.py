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
from datetime import datetime
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


def fetch_org_repos(org_name: str, token: Optional[str] = None) -> List[Dict]:
    """
    Fetch public repositories for a GitHub organization.
    
    Args:
        org_name: Name of the GitHub organization
        token: Optional GitHub token for authentication
        
    Returns:
        List of repository information dictionaries
    """
    try:
        import requests
    except ImportError:
        logger.error("requests library not installed. Please install requirements.txt")
        sys.exit(1)
    
    url = f"https://api.github.com/orgs/{org_name}/repos"
    headers = {
        'Accept': 'application/vnd.github.v3+json',
    }
    
    if token:
        headers['Authorization'] = f'token {token}'
    
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


def extract_repo_info(repos: List[Dict]) -> List[Dict]:
    """
    Extract relevant information from repository data.
    
    Args:
        repos: List of repository data from GitHub API
        
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
        extracted.append(info)
    
    return extracted


def save_snapshot(org_name: str, repos_info: List[Dict]) -> None:
    """
    Save a snapshot of repository information to a JSON file.
    
    Args:
        org_name: Name of the organization
        repos_info: List of repository information
    """
    timestamp = datetime.utcnow().isoformat()
    snapshot = {
        'organization': org_name,
        'timestamp': timestamp,
        'repository_count': len(repos_info),
        'repositories': repos_info
    }
    
    filename = f"snapshots/{org_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('snapshots', exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    logger.info(f"Snapshot saved to {filename}")


def display_summary(org_name: str, repos_info: List[Dict]) -> None:
    """
    Display a summary of the repository information.
    
    Args:
        org_name: Name of the organization
        repos_info: List of repository information
    """
    print(f"\n{'='*80}")
    print(f"Organization: {org_name}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Total public repositories: {len(repos_info)}")
    print(f"{'='*80}\n")
    
    if repos_info:
        print("Recently updated repositories:")
        print(f"{'Repository':<40} {'Updated':<20} {'Stars':<8} {'Language':<15}")
        print(f"{'-'*80}")
        
        for repo in repos_info[:10]:  # Show top 10 most recently updated
            name = repo['name'][:38] + '..' if len(repo['name']) > 38 else repo['name']
            updated = repo['updated_at'][:10]
            stars = str(repo['stars'])
            language = (repo['language'] or 'N/A')[:13]
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
        # Fetch repositories
        repos = fetch_org_repos(org_name, token)
        
        # Extract relevant information
        repos_info = extract_repo_info(repos)
        
        # Display summary
        display_summary(org_name, repos_info)
        
        # Save snapshot
        save_snapshot(org_name, repos_info)
        
        logger.info("Repository monitoring completed successfully")
        
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
