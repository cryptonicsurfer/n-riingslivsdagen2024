import streamlit as st
import os
import requests
from dotenv import load_dotenv
import base64
from google.cloud import storage
from google.oauth2 import service_account
from openai import OpenAI



# Load environment variables
# load_dotenv()
api_key = st.secrets['STABILITY_API_KEY']
api_host = os.getenv('API_HOST', 'https://api.stability.ai')

OPENAI_API_KEY = st.secrets['OPENAI_API_KEY']

#initialize openai as client
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


# Create a credentials object using the service account info from the secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


# Initialize Google Cloud Storage client
storage_client = storage.Client(credentials=credentials)
bucket = storage_client.bucket('falkenberg.tech')

if api_key is None:
    raise Exception("Missing Stability API key.")

# Streamlit UI
st.title("Image Generator")
user_input = st.text_input('Enter your prompt here:')
user_name = st.text_input('Enter your name:')
style_choice = st.radio('Välj en stil', ('AI-stil', 'Naturlig'))
submit = st.button('Generate Image')



if submit and user_input and user_name:
    st.write('Image generating...')

    english_input = translate_prompt(user_input)
    curated_prompt = f'{english_input}, cyberpunk, synthwave, photorealistic'

    # Choose prompt based on style
    prompt_to_use = english_input if style_choice == 'Naturlig' else curated_prompt

    # API request
    response = requests.post(
        f"{api_host}/v1/generation/stable-diffusion-v1-6/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "text_prompts": [{"text": curated_prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        },
    )

    if response.status_code == 200:
        data = response.json()
        for i, image in enumerate(data["artifacts"]):
            # Decode the base64 image
            image_bytes = base64.b64decode(image["base64"])
            
            # Create blob in Google Cloud Storage
            blob = bucket.blob(f"{user_input} {user_name}.png")
            blob.upload_from_string(image_bytes, content_type='image/png')
            
            st.success('Image saved successfully.')
    else:
        st.error("Failed to generate image: " + str(response.text))
