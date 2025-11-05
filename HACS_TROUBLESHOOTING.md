# HACS Installation Troubleshooting

## Common HACS Installation Issues

### "Could not download, see log for details"

This error can occur for several reasons. Here are the solutions:

#### Solution 1: Wait for Release Processing
If you just added the repository:
1. **Wait 5-10 minutes** for GitHub to process the release
2. **Refresh HACS** and try again
3. **Check GitHub Actions** are complete at: https://github.com/mediflowernz/ha-irrigation-addon/actions

#### Solution 2: Clear HACS Cache
1. Go to **HACS** → **Settings**
2. Click **Clear Cache**
3. Restart Home Assistant
4. Try installing again

#### Solution 3: Re-add Repository
1. **Remove** the custom repository from HACS
2. **Wait 2 minutes**
3. **Re-add** the repository:
   - URL: `https://github.com/mediflowernz/ha-irrigation-addon`
   - Category: **Integration**
4. **Install** the integration

#### Solution 4: Check HACS Logs
1. Go to **Settings** → **System** → **Logs**
2. Look for **HACS** related errors
3. Common issues:
   - Network connectivity
   - GitHub rate limiting
   - Repository access issues

### "Repository not found" Error

If HACS says the repository doesn't exist:

1. **Verify URL**: `https://github.com/mediflowernz/ha-irrigation-addon`
2. **Check Category**: Must be "Integration"
3. **Repository Access**: Ensure repository is public (it is)

### Manual Installation Alternative

If HACS continues to fail, use manual installation:

1. **Download Latest Release**:
   - Go to: https://github.com/mediflowernz/ha-irrigation-addon/releases
   - Download the latest release

2. **Extract Files**:
   ```
   /config/custom_components/irrigation_addon/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   └── ... (all other files)
   ```

3. **Restart Home Assistant**

4. **Add Integration**:
   - Settings → Devices & Services
   - Add Integration
   - Search "Irrigation Addon"

### Verification Steps

After successful installation, verify:

1. **Integration Listed**: In Settings → Devices & Services
2. **Files Present**: Check `/config/custom_components/irrigation_addon/`
3. **No Errors**: Check Home Assistant logs
4. **Services Available**: Check Developer Tools → Services

### Getting Help

If problems persist:

1. **Check GitHub Issues**: https://github.com/mediflowernz/ha-irrigation-addon/issues
2. **Create New Issue**: Include:
   - Home Assistant version
   - HACS version
   - Error messages from logs
   - Installation method attempted

3. **Community Support**: https://github.com/mediflowernz/ha-irrigation-addon/discussions

## HACS Requirements Checklist

Ensure your setup meets requirements:

- ✅ **HACS Installed**: Version 1.6.0 or newer
- ✅ **Home Assistant**: Version 2023.1.0 or newer
- ✅ **Internet Access**: For downloading from GitHub
- ✅ **Repository Public**: (This repository is public)
- ✅ **Correct Category**: Integration (not Add-on)

## Alternative Installation Methods

### Method 1: Git Clone (Advanced)
```bash
cd /config/custom_components/
git clone https://github.com/mediflowernz/ha-irrigation-addon.git irrigation_addon
```

### Method 2: Direct Download
1. Download repository as ZIP
2. Extract `custom_components/irrigation_addon/` folder
3. Copy to `/config/custom_components/irrigation_addon/`

### Method 3: HACS Custom Repository
1. HACS → Integrations
2. Three dots → Custom repositories
3. URL: `https://github.com/mediflowernz/ha-irrigation-addon`
4. Category: Integration
5. Add → Install

## Success Indicators

Installation successful when you see:

1. **HACS**: "Irrigation Addon" listed in installed integrations
2. **Home Assistant**: Integration available in Settings → Devices & Services
3. **Logs**: No error messages related to irrigation_addon
4. **Files**: All files present in custom_components directory

## Repository Status

- **Status**: ✅ Active and maintained
- **HACS Compatible**: ✅ Yes
- **Latest Release**: v1.0.0
- **GitHub Actions**: ✅ Passing
- **Documentation**: ✅ Complete

Your irrigation system should install successfully using any of these methods!