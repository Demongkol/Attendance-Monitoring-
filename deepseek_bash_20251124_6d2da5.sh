#!/bin/bash
echo "Installing requirements for Attendance System..."

# Update packages
pkg update && pkg upgrade -y

# Install Python and required packages
pkg install python -y
pkg install libjpeg-turbo -y
pkg install zlib -y

# Install Python packages
pip install opencv-python
pip install pillow
pip install qrcode
pip install pandas
pip install matplotlib
pip install numpy

# Install Termux API for camera access
pkg install termux-api -y

echo "Installation complete!"
echo "Make sure to grant camera permissions to Termux in app settings"