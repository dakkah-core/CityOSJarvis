# CityOSJarvis Build & Deploy Scripts

## Desktop Build

### Prerequisites
- Rust/Cargo (1.75+)
- pnpm
- Node.js 20+

### Build
```bash
# macOS
./scripts/build-desktop.sh macos

# Windows
.\scripts\build-desktop.ps1 windows

# Linux
./scripts/build-desktop.sh linux

# All platforms
./scripts/build-desktop.sh all
```

Outputs: `apps/cityos-jarvis-desktop/src-tauri/target/release/bundle/`

### Code Signing

**macOS**: Configure `APPLE_SIGNING_IDENTITY` env var or set in `tauri.conf.json`
**Windows**: Configure `WINDOWS_CERTIFICATE_THUMBPRINT` env var
**Linux**: AppImage requires no signing

### Auto-Updater
Configured in `tauri.conf.json`:
```json
"updater": {
  "active": true,
  "endpoints": ["https://api.dakkah.city/updates/cityos-jarvis-desktop/{{target}}/{{current_version}}"]
}
```

## Mobile Build

### Prerequisites
- EAS CLI: `npm install -g eas-cli`
- Expo account with build credits

### Build
```bash
cd apps/mobile
eas build --profile production

cd apps/mobile-inspector
eas build --profile production

cd apps/mobile-driver
eas build --profile production
```

### Configure
Update `eas.json` in each app with:
- `API_URL`: Backend endpoint
- `ASC_APP_ID` / `ASC_TEAM_ID`: Apple App Store Connect IDs
- `serviceAccountKeyPath`: Google Play service account
