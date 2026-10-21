#!/bin/sh
VERSION=$(git describe --tags 2>/dev/null || echo "0.0.0")
case "$1" in
  release) npm run build -- --mode production ;;
  *) echo "usage: $0 release" && exit 1 ;;
esac
tar -czf "dist-$VERSION.tgz" dist/ && ls -la dist-*.tgz | awk '{print $5, $9}'
