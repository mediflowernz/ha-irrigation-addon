#!/bin/bash

echo "Initializing Git repository for Home Assistant Irrigation Addon"
echo "================================================================"

echo ""
echo "Step 1: Initializing git repository..."
git init

echo ""
echo "Step 2: Adding all files..."
git add .

echo ""
echo "Step 3: Creating initial commit..."
git commit -m "Initial commit: Complete irrigation addon implementation

- Core irrigation control system with coordinator, models, and storage
- Professional web interface with real-time updates
- Comprehensive testing suite with unit, integration, and frontend tests
- HACS compatibility with proper manifest and structure
- Full documentation including installation, configuration, and troubleshooting
- GitHub Actions for CI/CD with automated testing and releases
- Fail-safe mechanisms for over-watering prevention
- Light schedule integration for optimal growing conditions
- Multi-room support for professional cultivation facilities"

echo ""
echo "Step 4: Adding GitHub remote..."
git remote add origin https://github.com/mediflowernz/ha-irrigation-addon.git

echo ""
echo "Step 5: Pushing to GitHub..."
git push -u origin main

echo ""
echo "================================================================"
echo "Git repository initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Go to https://github.com/mediflowernz/ha-irrigation-addon"
echo "2. Verify all files are uploaded correctly"
echo "3. Configure repository settings as described in setup_github.md"
echo "4. Create your first release with: git tag -a v1.0.0 -m 'Initial release'"
echo "================================================================"