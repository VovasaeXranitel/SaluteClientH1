import requests
import sounddevice as sd
import json
import io
import scipy.io.wavfile as wav
import time

# Загружаем настройки
with open("config.json", encoding='utf-8') as f:
    config = json.load(f)

INPUT_DEVICE = config["input_device_id"]
OUTPUT_DEVICE = config["output_device_id"]
GIGACHAT_AUTH_KEY = config["gigachat_auth_key"]
SBER_SALUTE_AUTH_KEY = config["salute_auth_key"]

SAMPLE_RATE = 16000

def record_audio(duration, device):
    print("🎤 Говорите...")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, device=device, dtype='int16')
    sd.wait()
    print("Запись завершена.")
    return audio.flatten()

def transcribe_audio(audio_bytes, salute_token):
    url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"
    headers = {
        'Authorization': f'Bearer {salute_token}',
        "Content-Type": "audio/x-pcm;bit=16;rate=16000"
    }
    response = requests.post(url, headers=headers, data=audio_bytes, verify=False)
    if response.ok:
        return response.json()['result'][0]
    print("STT:", response.text)
    return "речь не распознана, повторите"

def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = {'scope': 'GIGACHAT_API_PERS'}
    headers = {
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '5c107b81-fa83-408d-a7ff-426eec35e0e8'
    }
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.ok:
        print("GigaChat токен получен.")
        return response.json().get("access_token")
    print("Ошибка GigaChat токена:", response.text)
    return None

def get_salute_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = {'scope': 'SALUTE_SPEECH_PERS'}
    headers = {
        'Authorization': f'Basic {SBER_SALUTE_AUTH_KEY}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '5c107b81-fa83-408d-a7ff-426eec35e0e8'
    }
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.ok:
        print("SaluteSpeech токен получен.")
        return response.json().get("access_token")
    print("Ошибка SaluteSpeech токена:", response.text)
    return None

def ask_gigachat(question, token):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    data = {
        "model": "GigaChat-Pro",
        "messages": [{"role": "user", "content": question}]
    }
    response = requests.post(url, headers=headers, json=data, verify=False)
    if response.ok:
        return response.json()['choices'][0]['message']['content']
    print("GigaChat:", response.text)
    return "Ошибка генерации ответа."

def synthesize_speech(text, salute_token):
    url = "https://smartspeech.sber.ru/rest/v1/text:synthesize"
    headers = {
        "Authorization": f"Bearer {salute_token}",
        "Content-Type": "application/text",
        "Accept": "audio/wav"
    }
    response = requests.post(url, headers=headers, data=text.encode('utf-8'), verify=False)
    if response.ok:
        return response.content
    print("TTS:", response.text)
    return None

def play_audio(audio_bytes, device):
    try:
        rate, audio_array = wav.read(io.BytesIO(audio_bytes))
        sd.play(audio_array, rate, device=device)
        sd.wait()
    except Exception as e:
        print(f"Ошибка воспроизведения: {e}")

def refresh_tokens():
    return get_gigachat_token(), get_salute_token()

def main():
    giga_token, salute_token = refresh_tokens()

    if not giga_token or not salute_token:
        print("Ошибка получения токенов.")
        return

    while True:
        audio = record_audio(5, INPUT_DEVICE)
        text = transcribe_audio(audio.tobytes(), salute_token)
        print("Вы сказали:", text)

        if "выход" in text.lower():
            print("Завершение работы.")
            break

        if "Token has expired" in text or "Unauthorized" in text:
            giga_token, salute_token = refresh_tokens()
            continue

        answer = ask_gigachat(text, giga_token)
        print("GigaChat:", answer)

        audio_reply = synthesize_speech(answer, salute_token)
        if audio_reply:
            play_audio(audio_reply, OUTPUT_DEVICE)
        else:
            print("Ошибка TTS, ответ:", answer)

        time.sleep(0.5)

if __name__ == "__main__":
    main()
