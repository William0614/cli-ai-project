import sounddevice as sd

print("Available Audio Devices:")
print(sd.query_devices())

# Optional: Print default input device info
try:
    default_input_device_info = sd.query_devices(sd.default.device[0], 'input')
    print("\nDefault Input Device:")
    print(default_input_device_info)
except Exception as e:
    print(f"\nCould not query default input device: {e}")