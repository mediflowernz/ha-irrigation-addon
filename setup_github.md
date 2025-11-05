# GitHub Repository Setup Guide

This guide will help you set up the Home Assistant Irrigation Addon repository on GitHub.

## Prerequisites

- GitHub account (mediflowernz)
- Git installed on your local machine
- Repository files ready (already created)

## Step 1: Create GitHub Repository

1. **Go to GitHub**: Visit [github.com](https://github.com)
2. **Sign in** with your account: `mediflowernz`
3. **Create new repository**:
   - Click the "+" icon in the top right
   - Select "New repository"
   - Repository name: `ha-irrigation-addon`
   - Description: `Professional Home Assistant irrigation control system for cannabis cultivation`
   - Set to **Public** (for HACS compatibility)
   - **Do NOT** initialize with README, .gitignore, or license (we have these already)
   - Click "Create repository"

## Step 2: Initialize Local Repository

Open terminal/command prompt in your project directory and run:

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Complete irrigation addon implementation

- Core irrigation control system
- Professional web interface
- Comprehensive testing suite
- HACS compatibility
- Full documentation"

# Add GitHub remote
git remote add origin https://github.com/mediflowernz/ha-irrigation-addon.git

# Push to GitHub
git push -u origin main
```

## Step 3: Configure Repository Settings

### Branch Protection
1. Go to **Settings** → **Branches**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Require pull request reviews before merging
   - ✅ Dismiss stale PR approvals when new commits are pushed

### Repository Topics
1. Go to **Settings** → **General**
2. Add topics:
   - `home-assistant`
   - `irrigation`
   - `cannabis`
   - `hydroponics`
   - `automation`
   - `hacs`
   - `custom-integration`

### Enable Features
1. **Issues**: ✅ Enabled
2. **Discussions**: ✅ Enabled
3. **Wiki**: ✅ Enabled
4. **Projects**: ✅ Enabled

## Step 4: Set Up HACS Compatibility

### Create HACS Manifest
The `hacs.json` file is already created with:
```json
{
  "name": "Irrigation Addon",
  "hacs": "1.6.0",
  "domains": ["irrigation_addon"],
  "iot_class": "Local Polling",
  "homeassistant": "2023.1.0"
}
```

### HACS Submission (Optional)
To submit to HACS default repository:
1. Ensure repository meets [HACS requirements](https://hacs.xyz/docs/publish/integration)
2. Create issue in [HACS/default](https://github.com/hacs/default) repository
3. Follow submission guidelines

## Step 5: Configure GitHub Actions

The following workflows are already set up:

### Tests Workflow (`.github/workflows/tests.yml`)
- Runs on push/PR to main/develop branches
- Tests Python 3.8-3.11
- Includes linting and HACS validation
- Uploads coverage reports

### Release Workflow (`.github/workflows/release.yml`)
- Triggers on version tags (v1.0.0, v1.1.0, etc.)
- Runs full test suite
- Creates GitHub releases automatically
- Updates manifest version

## Step 6: Create First Release

### Tag and Release
```bash
# Create and push version tag
git tag -a v1.0.0 -m "Release v1.0.0: Initial release

Features:
- Complete irrigation control system
- Professional web interface  
- Comprehensive testing
- HACS compatibility
- Full documentation"

git push origin v1.0.0
```

This will automatically trigger the release workflow and create a GitHub release.

## Step 7: Repository Documentation

### Update Repository Description
1. Go to repository main page
2. Click the gear icon next to "About"
3. Add description: `Professional Home Assistant irrigation control system for cannabis cultivation`
4. Add website: `https://github.com/mediflowernz/ha-irrigation-addon`
5. Add topics (as listed above)

### Create Wiki Pages
1. Go to **Wiki** tab
2. Create pages:
   - **Home**: Overview and quick start
   - **Installation**: Detailed installation guide
   - **Configuration**: Configuration examples
   - **Troubleshooting**: Common issues and solutions
   - **API Reference**: Service and entity documentation

## Step 8: Community Setup

### Enable Discussions
1. Go to **Settings** → **General**
2. Enable **Discussions**
3. Create categories:
   - **General**: General questions and discussion
   - **Ideas**: Feature requests and suggestions
   - **Q&A**: Questions and answers
   - **Show and tell**: User setups and configurations

### Issue Templates
Issue templates are already created:
- Bug report template
- Feature request template
- Pull request template

## Step 9: Security and Maintenance

### Security Policy
Create `.github/SECURITY.md`:
```markdown
# Security Policy

## Reporting Security Vulnerabilities

Please report security vulnerabilities privately by emailing:
[your-email@domain.com]

Do not create public issues for security problems.
```

### Dependabot (Optional)
Create `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

## Step 10: Promotion and Distribution

### HACS Installation URL
Users can install via HACS using:
```
https://github.com/mediflowernz/ha-irrigation-addon
```

### Community Sharing
- Share in Home Assistant Community Forum
- Post in relevant Reddit communities
- Share in cannabis cultivation forums (where legal)

## Maintenance Commands

### Regular Updates
```bash
# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/new-feature

# Make changes, commit, and push
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# Create pull request on GitHub
```

### Release Process
```bash
# Update version in manifest.json
# Update CHANGELOG.md
# Commit changes
git add .
git commit -m "Prepare release v1.1.0"
git push origin main

# Create and push tag
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## Repository Structure

Your repository now includes:

```
ha-irrigation-addon/
├── .github/
│   ├── workflows/
│   │   ├── tests.yml
│   │   └── release.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── pull_request_template.md
├── custom_components/irrigation_addon/
├── tests/
├── docs/
├── .gitignore
├── CONTRIBUTING.md
├── README.md
├── CHANGELOG.md
├── LICENSE
└── hacs.json
```

## Next Steps

1. **Test the setup**: Clone the repository to verify everything works
2. **Create documentation**: Add detailed wiki pages
3. **Engage community**: Respond to issues and discussions
4. **Continuous improvement**: Regular updates and feature additions

Your repository is now ready for professional development and community collaboration!