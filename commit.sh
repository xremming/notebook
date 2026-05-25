#!/bin/bash

set -eo pipefail

git add .
git commit -m "Auto-commit by $USER@$HOSTNAME at $(date -R)"
git pull
git push
