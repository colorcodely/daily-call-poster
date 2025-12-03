import os
import time
import requests
from twilio.rest import Client
from openai import OpenAI

TWILIO_SID = os.environ["TWILIO_SID"]
TWILIO_AUTH = os.environ["TWILIO_AUTH"]
TWILIO_FROM = os.environ["TWILIO_FROM"]
TWILIO_TO = os.environ["TWILIO_TO"]
TWILIO_TWIML_URL = os.environ["TWILIO_TWIML_URL"]

FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]

client = Client(TWILIO_SID, TWILIO_AUTH)
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def place_call_and_get_recording():
    print("Placing outbound call...")

    call = client.calls.create(
        to=TWILIO_TO,
        from_=TWILIO_FROM,
        url=TWILIO_TWIML_URL,
        record=True
    )

    call_sid = call.sid
    print("Call SID:", call_sid)

    # Wait for call to finish + recording to generate
    print("Waiting for recording...")
    recording = None

    for _ in range(30):  # 30 retries × 10 sec = 5 minutes max
        recs = client.recordings.list(call_sid=call_sid)
        if recs:
            recording = recs[0]
            break
        time.sleep(10)

    if not recording:
        raise RuntimeError("No recording produced by Twilio.")

    print("Recording found:", recording.sid)

    # Download audio file
    recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Recordings/{recording.sid}.mp3"
    audio = requests.get(recording_url, auth=(TWILIO_SID, TWILIO_AUTH)).content

    with open("call.mp3", "wb") as f:
        f.write(audio)

    print("Recording downloaded.")
    return "call.mp3"


def transcribe_audio(path):
    print("Transcribing audio...")
    with open(path, "rb") as f:
        transcript = openai_client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=f
        )
    text = transcript.text
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
        print("Facebook error:", r.text)
        raise RuntimeError("Failed posting to Facebook.")

    print("Posted successfully.")
    return True


if __name__ == "__main__":
    audio_file = place_call_and_get_recording()
    text = transcribe_audio(audio_file)
    post_to_facebook(text)
