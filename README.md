# Definition Processing API

A simple web server for processing definition templates with language and industry customization.

## Setup

1. Clone the repository
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure your environment variables in `.env`:
   ```
   # Authentication
   API_TOKEN=your_secure_token

   # API Keys
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GOOGLE_API_KEY=your_google_api_key

   # Server configuration
   PORT=5000
   ```

## Running the Server

```
python main.py
```

The server will start on port 5000 by default (can be changed in `.env` file).

## API Endpoints

### Process Definition

```
POST /process
```

Processes a definition template with language and industry customization.

#### Authentication

Bearer token authentication is required. Include an `Authorization` header with the format: `Bearer your_token`, where `your_token` matches the `API_TOKEN` value set in the `.env` file.

Example:
```
Authorization: Bearer your_secure_token
```

#### Request Body

```json
{
    "vendor": "anthropic",
    "locale": "en-US",
    "industry": "Plumbing",
    "definition": "{\"templates\": [...], \"products\": [...], ...}"
}
```

- `vendor`: The AI vendor to use for processing. Either `anthropic` or `google`.
- `locale`: The locale code for language. Supported values: `en-US`, `ru`, `es-ES`.
- `industry`: The industry to customize the definition for.
- `definition`: The base definition string to process.

#### Response

```json
{
    "result": "processed_definition_here"
}
```

### Health Check

```
GET /health
```

Returns a simple health status to check if the server is running.

#### Response

```json
{
    "status": "healthy"
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request`: Missing required parameters
- `401 Unauthorized`: Missing or invalid Bearer token
- `500 Internal Server Error`: Server-side processing errors

## Example Request with cURL

```bash
curl -X POST http://localhost:5000/process \
  -H "Authorization: Bearer your_secure_token" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "anthropic",
    "locale": "en-US",
    "industry": "Plumbing",
    "definition": "your_base_definition_here"
  }'
```
