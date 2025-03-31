import sounddevice as sd

def list_devices():
    devices = sd.query_devices()

    print("Устройства ввода:")
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"{idx}: {dev['name']}")

    print("\nУстройства вывода:")
    for idx, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            print(f"{idx}: {dev['name']}")

if __name__ == "__main__":
    list_devices()
