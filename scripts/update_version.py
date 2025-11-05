#!/usr/bin/env python3
"""Script to update version across all files."""

import json
import re
import sys
from pathlib import Path

def update_manifest_version(version: str) -> None:
    """Update version in manifest.json."""
    manifest_path = Path("custom_components/irrigation_addon/manifest.json")
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    manifest["version"] = version
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Updated manifest.json to version {version}")

def update_changelog(version: str) -> None:
    """Update CHANGELOG.md with new version."""
    changelog_path = Path("CHANGELOG.md")
    
    with open(changelog_path, "r") as f:
        content = f.read()
    
    # Replace [Unreleased] with new version
    today = "2024-11-06"  # You might want to use datetime.now().strftime("%Y-%m-%d")
    content = content.replace(
        "## [Unreleased]",
        f"## [Unreleased]\n\n## [{version}] - {today}"
    )
    
    with open(changelog_path, "w") as f:
        f.write(content)
    
    print(f"Updated CHANGELOG.md with version {version}")

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <version>")
        print("Example: python update_version.py 1.0.1")
        sys.exit(1)
    
    version = sys.argv[1]
    
    # Validate version format (basic semver)
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print("Error: Version must be in format X.Y.Z (e.g., 1.0.1)")
        sys.exit(1)
    
    update_manifest_version(version)
    update_changelog(version)
    
    print(f"\nVersion updated to {version}")
    print("Don't forget to:")
    print("1. Commit the changes")
    print("2. Create a git tag: git tag v{version}")
    print("3. Push the tag: git push origin v{version}")

if __name__ == "__main__":
    main()