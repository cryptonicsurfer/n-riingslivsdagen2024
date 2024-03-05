import streamlit as st
import requests
import base64
from google.cloud import storage
from google.oauth2 import service_account
from openai import OpenAI

# Initialize OpenAI client with secrets
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
st.title("Näringslivsdagen 2024")
st.header("Skapa en AI bild")

# Using Streamlit form functionality
with st.form(key='image_creation_form', clear_on_submit=True):
    user_input = st.text_area('Prompt:', key="user_input_prompt", placeholder="En dansande farbror med en grupp barn i en apelsinträdgård på våren.", help="Beskriv vad du vill se i din bild. Beskriv stil och omgivning. Var gärna detaljerad.")
    user_name = st.text_input('Ditt namn:', key="user_name_input")
    style_choice = st.radio("Välj en stil:", ('AI Style', 'Natural'), key="style_choice_radio")

    submit_button = st.form_submit_button('Skapa bild')

if submit_button:
    if user_input and user_name:
        st.write('Skapar bild... det tar cirka 10 sekunder... Håll ut.. ')
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
                blob = bucket.blob(f"{user_input} - {user_name}.png")
                blob.upload_from_string(image_bytes, content_type='image/png')
                
                st.success('Tack! Din bild är nu skapad!')
                st.image(image_bytes, caption=(f"{user_input} - {user_name}"))
                break  # Process only the first image
        else:
            st.error("Felmeddelande: " + str(response.text))
    else:
        st.error("Ange både prompt och ditt namn")
