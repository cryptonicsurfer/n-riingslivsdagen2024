import streamlit as st
import requests
import base64
from google.cloud import storage
from google.oauth2 import service_account
from openai import OpenAI

# Initialize OpenAI client
OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']
client = OpenAI(api_key=OPENAI_API_KEY)
llm = 'gpt-4-turbo-preview'

def translate_prompt(user_input):
    response = client.chat.completions.create(
        model=llm,
        messages=[
            {"role": "system", "content": "Du översätter från svenska till Engelska utan göra misstag eller ändra innebörd."},
            {"role": "user", "content": user_input},
        ]
    )
    return response.choices[0].message.content

# Google Cloud Storage setup
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
storage_client = storage.Client(credentials=credentials)
bucket = storage_client.bucket('falkenberg.tech')

# Streamlit UI
st.title("Testa att göra en AI bild med ord")

user_input = st.text_input('Skriv din text här', key="user_input", value="")
user_name = st.text_input('Skriv ditt namn här:', key="user_name", value="")
style_choice = st.radio("Choose a style:", ('AI Style', 'Natural'), key="style_choice")

if st.button('Generate Image'):
    if user_input and user_name:
        st.write('Image generating...')
        english_input = translate_prompt(user_input)
        curated_prompt = f'{english_input}, cyberpunk, synthwave, photorealistic'

        prompt_to_use = english_input if style_choice == 'Natural' else curated_prompt

        api_key = st.secrets['STABILITY_API_KEY']
        api_host = 'https://api.stability.ai'

        # API request
        response = requests.post(
            f"{api_host}/v1/generation/stable-diffusion-v1-6/text-to-image",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "text_prompts": [{"text": prompt_to_use}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            },
        )

        if response.status_code == 200:
            data = response.json()
            for image in data["artifacts"]:
                image_bytes = base64.b64decode(image["base64"])
                blob = bucket.blob(f"{user_input} {user_name}.png")
                blob.upload_from_string(image_bytes, content_type='image/png')
                
                st.success('Image saved successfully.')
                st.image(image_bytes, caption="Generated Image")
                # Clear input after successful generation
                st.session_state.user_input = ''
                st.session_state.user_name = ''
                break  # Assuming you want to process only the first image for now
        else:
            st.error("Failed to generate image: " + str(response.text))
    else:
        st.error("Please enter both a prompt and your name.")
