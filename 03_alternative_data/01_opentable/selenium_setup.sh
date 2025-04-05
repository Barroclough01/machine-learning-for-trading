#!/usr/bin/env bash
# get latest - https://github.com/mozilla/geckodriver/releases
curl -L -o geckodriver.zip https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-win64.zip
unzip geckodriver.zip
# Create a directory in your user profile if it doesn't exist
mkdir -p "$HOME/bin"
mv geckodriver.exe "$HOME/bin/"
# Clean up the zip file
rm geckodriver.zip