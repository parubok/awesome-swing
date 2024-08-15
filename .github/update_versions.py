import os
import re
from datetime import datetime
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv


# Load environment variables from the .env file
load_dotenv()
api_token = os.getenv('API_TOKEN')

# Initialize a requests session
session = requests.Session()
session.headers.update({
    'Accept': 'application/vnd.github+json',
    'Authorization': f'Bearer {api_token}'
})


def get_latest_release(repo: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieves the latest release version and release date for a given repository.
    """

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = session.get(url)
    if response.status_code == 200:
        release = response.json()
        return release["tag_name"], release["published_at"]
    else:
        return None, None


def extract_version(value: str) -> Optional[str]:
    """
    Extracts the numerical version from a string.
    """

    match = re.search(r'\d+(?:[.\-_]\d+){1,3}', value)
    return match.group(0).replace('-', '.').replace('_', '.') if match else None


def process_row(row: str) -> str:
    """
    Processes a row to extract the release version and updates it if a newer version is available.
    """

    columns = row.split('|')

    if len(columns) != 4:
        return row

    # Extracts only GitHub repository URLs
    repo_url_match = re.search(r'\((https://github\.com/[^/]+/[^/]+)\)', columns[0].strip())
    if not repo_url_match:
        return row

    repo_url = repo_url_match.group(1)
    repo = repo_url.split("github.com/")[1]

    latest_version, latest_release_date = get_latest_release(repo)
    if latest_version is None:
        return row

    latest_version = extract_version(latest_version)
    current_version = extract_version(columns[3].split('/')[0])

    if current_version == latest_version:
        return row

    date = datetime.strptime(latest_release_date, '%Y-%m-%dT%H:%M:%SZ').strftime('%b %d, %Y')
    columns[3] = f" {latest_version} / {date} "

    print(f"Updating: {repo_url} {current_version} -> {latest_version} {date}")
    return '|'.join(columns)


def update_readme_table(file_path: str) -> None:
    """
    Updates the table in README.md with the latest versions and release dates.
    """

    table_start_marker: str = "<!-- TABLE_START -->"
    table_end_marker: str = "<!-- TABLE_END -->"

    with open(file_path, "r") as file:
        readme_content = file.read()

    table_start = readme_content.find(table_start_marker) + len(table_start_marker) + 1
    table_end = readme_content.find(table_end_marker) - 1

    if table_start == -1 or table_end == -1:
        raise ValueError("Table markers not found in README.md")

    table_content = readme_content[table_start:table_end]
    lines = table_content.strip().split('\n')
    header, separator, *rows = lines

    updated_rows = []
    for row in rows:
        updated_rows.append(process_row(row))

    updated_table_content = '\n'.join([header, separator] + updated_rows)

    updated_readme_content = (
        readme_content[:table_start]
        + updated_table_content
        + readme_content[table_end:]
    )

    with open(file_path, "w") as file:
        file.write(updated_readme_content)


if __name__ == "__main__":
    update_readme_table("README.md")
