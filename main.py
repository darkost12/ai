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

def base_definition_text(base_definition):
    if base_definition is None:
        return ""
    else:
        return "Use following definition as a base for your output:\n" + base_definition

def process_definition(provider, locale, industry, base_definition):
    LANGUAGE = language(locale)

    contents = """
        You are asked to generate a JSON definition for a new tenant.
        Output valid JSON only. Do not include any comments, explanations, or extra properties.

        --- SCHEMA
        The JSON must contain these top-level arrays:
        { "catalog_units": [...], "categories": [...], "products": [...], "services": [...], "templates": [...] }

        ### catalog_units
        - Objects: {id:string, name:string, code:string, type:"products"|"services", system:boolean (only for type:"services")}
        - Exactly 3:
          - 1 service catalog unit, must include id:"catalog_unit-0", code:"service", type:"services", system:true and name in {LANGUAGE}
          - 2 product catalog units, with {INDUSTRY}-specific names and codes

        ### categories
        - Objects: {id:string, name:string, type:"products"|"services", archived:boolean}
        - Exactly 2: 1 for products, 1 for services

        ### products
        - Objects: {id:string, name:string, currency:string (ISO-4217 lowercase), unit:string (catalog_unit id), category:string (category id, optional), price_default:string (decimal, optional), archived:boolean}
        - Exactly 2

        ### services
        - Objects: {id:string, name:string, currency:string (ISO-4217 lowercase), unit:string (catalog_unit id), category:string (category id, optional), price_default:string (decimal, optional), archived:false}
        - Exactly 2

        ### templates
        - Objects: {id:string, name:string, job_type:"job_type-0", possible_resolutions:["resolution-0","resolution-1"], scheduled_duration_min:integer, can_be_used_on_mobile:true, custom_fields:object[], report_fields:object[]}
        - Exactly 5
        - Each template must contain:
          - ≥2 custom_fields
          - ≥5 report_fields

        ### custom_fields
        Object properties:
        - {id:string, type:string, name:string, field_type:string, data_type:string}

        ### report_fields
        Object properties:
        - Same as custom_fields
        - Plus: required:boolean (default true), signed_field:string (only if field_type == "signature")

        --- FIELD_TYPE ⇄ DATA_TYPE (valid combinations only)
        Custom fields:
        - currency → currency
        - input → string | decimal | integer
        - file → attachment
        - button → boolean
        - dictionary → dictionary
        - link → url
        - date → date_picker
        - time → time_picker
        - datetime → datetime_picker

        Report fields:
        - Same as custom field combinations
        - Plus:
          - image → attachment
          - signature → attachment
            - must represent **customer signature** only
            - must include signed_field referencing a **custom_field of type:"file"** from the same template representing some document
          - checkbox → boolean

        --- CARDINALITY
        - catalog_units: 3 (2 products, 1 service with fixed name/code)
        - categories: 2 (1 product, 1 service)
        - products: 2
        - services: 2
        - templates: 5 (≥2 custom_fields, ≥5 report_fields each)

        --- ID RULES
        - IDs must follow sequential, end-to-end order per entity type:
          - catalog_units: catalog_unit-0 … catalog_unit-2
          - categories: category-0 … category-1
          - products: product-0 … product-1
          - services: service-0 … service-1
          - templates: template-0 … template-4
        - **custom_fields and report_fields share one global counter across ALL templates:**
          - IDs and types start at custom_field-0 and custom_field_type-0 in the first template and increment continuously across all templates.
          - Example: if template-0 has 2 custom_fields + 5 report_fields, their IDs are custom_field-0 … custom_field-6. Template-1 continues with custom_field-7, etc.
        - signed_field in a signature report_field must point only to a **file-type custom_field** from the same template.

        --- CONTENT
        - All names, codes, and values must be realistic and relevant to the {INDUSTRY} and in {LANGUAGE}.
        - Use lowercase ISO-4217 for currency.
        - Use decimal strings for price_default (e.g., "12.50").
        - All references (unit, category, signed_field) must point to existing IDs defined in this JSON.

        --- OUTPUT
        Return only the JSON object.

    """.replace('{INDUSTRY}', industry).replace('{LANGUAGE}', LANGUAGE) + base_definition_text(base_definition)

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
        "definition": "base definition maybe"
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
        definition = data.get('definition', None)

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
    app.debug = True
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
