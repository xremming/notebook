#!/bin/bash

git add .
git commit -m "Auto-commit by $USER@$HOSTNAME at $(date -R)"
git push
