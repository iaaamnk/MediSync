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

cd flutter_frontend

# Configure and generate web platform scaffolding if not present
echo "Configuring web platform..."
flutter config --enable-web
flutter create . --platforms web

# Get dependencies and compile web release
echo "Running flutter pub get..."
flutter pub get

echo "Building Flutter Web release..."
flutter build web --release

echo "=== Flutter Web Build Complete! Output at flutter_frontend/build/web ==="
