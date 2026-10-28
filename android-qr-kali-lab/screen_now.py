import qrcode

# Replace with your link or text
data = "https://kali.org"

# Generate and show the QR code
img = qrcode.make(data)
img.show()
