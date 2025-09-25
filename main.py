from anthropic import Anthropic
from google import genai
import time
import os
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Bearer token authentication
# In a production environment, use a more secure token management system
API_TOKEN = os.environ.get("API_TOKEN", "default_token")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if auth_header:
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        if token != API_TOKEN:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated

def language(locale):
    if locale == 'ru':
        return 'Russian'
    elif locale == 'es-ES':
        return 'Spanish'
    else:
        return 'English'

def process_definition(provider, locale, industry, base_definition):
    LANGUAGE = language(locale)

    contents = f"""
        We use definition to create new tenants with specific settings. They depend on tenants industry and locale. Example of definition:
        {base_definition}

        Based on the base definition example create a new definition in {LANGUAGE} relevant to the {industry} industry.
        - Adhere to schema, don't add comments or invent new field types.
        - Custom fields are filled before job is started with some information about the job. Report fields are used during and after job completion.
        - Entries in custom_fields can have field_type of text, currency, input, button, dictionary, link, date, datetime, time.
        - Entries in report_fields can have same field types plus image, action, checkbox, signature. Signature field requires additional property signed_field which references custom field of file type. Currency field requires additional properties currency, use_currency_fractional_unit, use_currency_fractional_unit_type.
        - Generate exactly 5 templates.
        - Output valid JSON only.

        Output:
    """

    start = time.time()
    print("Starting generation")

    if provider == 'anthropic':
        API_KEY = os.environ.get("ANTHROPIC_API_KEY", "default_key")

        client = Anthropic(api_key=API_KEY)

        response = client.messages.create(
          model="claude-sonnet-4-0",
          max_tokens=10000,
          messages=[{"role": "user", "content": contents}]
        )
        result = response.content[0].text
    elif provider == 'google':
        API_KEY = os.environ.get("GOOGLE_API_KEY", "default_key")

        client = genai.Client(api_key=API_KEY)

        response = client.models.generate_content(
          model="gemini-2.5-flash", contents=contents
        )
        result = response.text
    elif provider == 'openai':
        API_KEY = os.environ.get("OPENAI_API_KEY", "default_key")

        client = OpenAI(api_key=API_KEY)

        response = client.chat.completions.create(
          model="gpt-4o",
          messages=[
            {"role": "user", "content": contents}
          ],
          temperature=0.3,
          max_tokens=10000
        )

        result = response.choices[0].message.content
    else:
        result = "Unsupported provider. Please use 'anthropic' or 'google' or 'openai'."

    end = time.time()
    print(f"Generation completed in {round(end - start, 2)} seconds")
    return result

@app.route('/definition', methods=['POST'])
@token_required
def process_endpoint():
    """
    Process definition endpoint

    Expected JSON body:
    {
        "provider": "anthropic",
        "locale": "en-US",
        "industry": "Plumbing",
        "definition": "base definition string here"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract required parameters from request
        provider = data.get('provider', 'anthropic')
        locale = data.get('locale', 'en-US')
        industry = data.get('industry', 'General')
        definition = data.get('definition')

        if not definition:
            return jsonify({"error": "No definition provided in request body"}), 400

        # Process the definition
        result = process_definition(provider, locale, industry, definition)
        print(result)
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    # Set to False in production
    app.debug = False
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
