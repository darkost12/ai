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
        We use definitions to create new tenants with relevant examples which depend on tenants industry and locale. Description of definition structure:
        - catalog_units are used to define units of measurement for products and services. Properties: id (string), name (string), code (string), type (string, one of "products", "services") and system (boolean, for "services" type only). Example:
            `catalog_units: [{id: "catalog_unit-0", name: "Piece", code: "pcs", type: "products"}, {id: "catalog_unit-1", name: "Service", code: "service", type: "services", system: true}]`
        - categories are used to group products and services. Properties: id (string), name (string), type ("products" or "services"), archived (boolean, false by default). Example:
            `categories: [{id: "category-0", name: "Installations", type: "services", archived: false}, {id: "category-1", name: "Pipes", type: "products", archived: false}]`
        - products are items that can be used in jobs as sold goods. Properties: id (string), name (string), currency (lowercase iso-4217 code string), unit (string referencing catalog_units id), category (string referencing categories id, optional), price_default (decimal string, optional), archived (boolean, false by default). Example:
            `products: [{id: "product-0", name: "Connector", currency: "usd", price_default: "3.00", unit: "catalog_unit-0", category: "category-1",archived: false}]`
        - services are provided during jobs. Properties: id (string), name (string), currency (lowercase iso-4217 code string), unit (string referencing catalog_units id), category (string referencing categories id, optional),price_default (decimal string, optional), archived (boolean, should be false for new services). Example:
            `services: [{id: "service-0", name: "Router Installation", currency: "usd", price_default: "10.00", unit: "catalog_unit-1", category: "category-0", archived: false}]`
        - templates describe sets of fields for a job. Properties: id (string), name (string), job_type (string, should be "job_type-0"), possible_resolutions (string[], should be ["resolution-0", "resolution-1"]), scheduled_duration_min (integer), can_be_used_on_mobile (boolean, should be true), custom_fields (object[]), report_fields (object[]).
            Custom fields are filled before job, they are not filled by workers. Properties: id (string), type (string), name (string), field_type (string, one of "currency", "input", "file", "button", "dictionary", "link", "date", "datetime", "time"), data_type (string, "attachment" for "file" field_type, "string" or "decimal" or "integer" for "input", "currency" for "currency", "dictionary" for "dictionary", "date_picker" for "date", "time_picker" for "time", "datetime_picker" for "datetime", "url" for "link", "boolean" for "button").
            Report fields are filled by worker during or after job execution. They have same properties as custom fields plus additional properties: required (boolean, true by default), signed_field (string referencing field id from custom_fields, only for "signature" field_type), field_type can also have values "image", "signature", "checkbox", data_type for "image" and "signature" is "attachment", "boolean" for "checkbox". Example:
            `templates: [{id: "template-0", type: "job_type-0", name: "Emergency", scheduled_duration_min: 120, can_be_used_on_mobile: true, possible_resolutions: ["resolution-0", "resolution-1"], custom_fields: [{id: "custom_field-0", type: "custom_field_type-0", name: "User agreement", field_type: "file", data_type: "attachment"}, {id: "custom_field-1", type: "custom_field_type-1", name: "Customer comment", field_type: "input", data_type: "string"}], report_fields: [{id: "custom_field-2", type: "custom_field_type-2", name: "Photo of the issue (before)", field_type: "image", data_type: "attachment", required: true}, {id: "custom_field-3", type: "custom_field_type-3", name: "Turn off electricity", field_type: "checkbox", data_type: "boolean", required: true}, {id: "custom_field-4", type: "custom_field_type-4", name: "Customer signature", field_type: "signature", data_type: "attachment", signed_field: "custom_field-0", required: true}]}]`
        """ + base_definition_text(base_definition) + f"""
        Based on example and restrictions create a new definition in {LANGUAGE} relevant to the {industry} industry.
        - Adhere to schema, don't add comments or invent new field types.
        - Generate one catalog unit for services with corresponding name and code and two for products with industry specific names; one category for products and one for services; two products and two services. There should be exactly five templates, each should have at least two custom fields and five report fields.
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
