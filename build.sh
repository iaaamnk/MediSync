#!/usr/bin/env bash
set -e

echo "=== Starting Flutter Web Build for Cloudflare Pages ==="

# Clone Flutter if not already cached
if [ ! -d "_flutter" ]; then
  echo "Cloning Flutter SDK (stable branch)..."
  git clone https://github.com/flutter/flutter.git --depth 1 -b stable _flutter
fi

# Add Flutter to PATH
export PATH="$(pwd)/_flutter/bin:$PATH"

echo "Flutter binary located at: $(which flutter)"
flutter --version

# Build Flutter Web App
cd flutter_frontend
flutter config --enable-web
flutter pub get
flutter build web --release

echo "=== Flutter Web Build Complete! Output at flutter_frontend/build/web ==="
