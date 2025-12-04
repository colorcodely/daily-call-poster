import os
import time
import requests
from twilio.rest import Client
import os.path

# Load environment variables
TWILIO_SID = os.environ["TWILIO_SID"]
TWILIO_AUTH = os.environ["TWILIO_AUTH"]
TWILIO_FROM = os.environ["TWILIO_FROM"]
TWILIO_TO = os.environ["TWILIO_TO"]
TWILIO_TWIML_URL = os.environ["TWILIO_TWIML_URL"]

FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Twilio client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)


def place_call_and_get_recording():
    print("Placing outbound call...")

    call = twilio_client.calls.create(
        to=TWILIO_TO,
        from_=TWILIO_FROM,
        url=TWILIO_TWIML_URL,
        record=True
    )

    call_sid = call.sid
    print(f"Call SID: {call_sid}")

    # Wait for call to finish + recording to generate
    print("Waiting for recording...")
    recording = None

    for _ in range(30):  # 30 retries × 10 sec = 5 minutes max
        recs = twilio_client.recordings.list(call_sid=call_sid)
        if recs:
            recording = recs[0]
            break
        time.sleep(10)

    if not recording:
        raise RuntimeError("No recording produced by Twilio.")

    print(f"Recording found: {recording.sid}")

    # Download audio file
    recording_url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{TWILIO_SID}/Recordings/{recording.sid}.mp3"
    )

    audio = requests.get(recording_url, auth=(TWILIO_SID, TWILIO_AUTH)).content

    with open("call.mp3", "wb") as f:
        f.write(audio)

    print("Recording downloaded.")
    return "call.mp3"


def transcribe_audio(path):
    print("Transcribing audio...")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    with open(path, "rb") as f:
        files = {
            "file": (os.path.basename(path), f, "audio/mpeg"),
        }
        data = {
            "model": "whisper-1",
        }

        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            data=data,
            files=files,
            timeout=120,
        )

    response.raise_for_status()

    result = response.json()
    text = result.get("text", "")
    print("Transcription complete.")
    return text


def post_to_facebook(message):
    print("Posting to Facebook...")

    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    data = {
        "message": message,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }

    r = requests.post(url, data=data)

    if r.status_code != 200:
        print(f"Facebook error: {r.text}")
        ra
