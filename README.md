# Backbone

Dynamic Summarization of Scientific Papers Using Profile-Aware AI 

Context:

In my current position at EURANOVA, I give a weekly presentation to all my colleagues on the latest developments in AI around the world, covering news, tools, scientific papers, and more. I scan the internet to identify trending events and hot topics related to AI and ML globally.

One section of the presentation is dedicated to scientific papers, where I summarize a recent advancement in the field. These summaries need to be brief and high-level because the audience is cross-functional—many colleagues do not have a deep technical background. Therefore, the presentation must be adapted to be easily understood by everyone.

Preparing this section typically takes me over an hour, as I read the paper, understand the underlying methods, evaluate the achievements, and consider how it could be relevant to the internal projects we are working on. To streamline this process, I decided to create an agent that can help me prepare the presentation by extracting highlights and key insights that I can directly use in my talk.

![Backbone Interface](assets/ss_04.png)

*Example of the Backbone interface showing PDF upload, processing, and content extraction*

## Architecture

This application is split into two separate services:

- **Frontend**: Gradio-based web interface 
- **Backend**: FastAPI document processor service 

The frontend automatically waits for the backend to be healthy before starting, ensuring users cannot make requests until the backend is ready.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)
- OpenAI API key (for AI report generation)
- Langfuse account and API keys (for prompt management)

## Environment Variables Setup

Before running the application, you need to create a `.env` file in the project root directory with the required environment variables.

### Creating the .env File

1. Create a `.env` file in the root directory of the project:
   ```bash
   touch .env
   ```

2. Add the following environment variables to the `.env` file:

```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Langfuse Configuration (Required)
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Prompt Configuration (Required)
PROMPT_NAME=backbone_prompt

# Language Configuration (Optional - defaults to "french")
LANGUAGE=french

# Model Configuration (Optional - defaults to "gpt-4o-mini")
MODEL=gpt-4o

# Backend URL (Optional - defaults to "http://backbone-backend:8000")
# Only needed if running services separately or with custom URLs
BACKEND_URL=http://backbone-backend:8000
```

### Environment Variables Explained

#### Required Variables

- **`OPENAI_API_KEY`**: Your OpenAI API key for generating AI reports. Get one at [platform.openai.com](https://platform.openai.com)
- **`LANGFUSE_SECRET_KEY`**: Your Langfuse secret key for accessing prompts. Get it from your Langfuse project settings
- **`LANGFUSE_PUBLIC_KEY`**: Your Langfuse public key for accessing prompts. Get it from your Langfuse project settings
- **`PROMPT_NAME`**: The name of the prompt stored in Langfuse that will be used for report generation (e.g., `backbone_prompt`)

#### Optional Variables

- **`LANGFUSE_BASE_URL`**: The base URL for your Langfuse instance. Defaults to `https://cloud.langfuse.com` if not specified. Change this if you're using a self-hosted Langfuse instance
- **`LANGUAGE`**: The language for report generation. Can be `"french"` or `"english"`. Defaults to `"french"` if not specified
- **`MODEL`**: The OpenAI model to use for report generation. Defaults to `"gpt-4o-mini"` if not specified. Options include:
  - `gpt-4o` (recommended for best quality)
  - `gpt-4o-mini` (faster and cheaper)
  - `gpt-4-turbo`
  - `gpt-4`
  - `gpt-3.5-turbo`
- **`BACKEND_URL`**: The URL of the backend service. Only needed if running services separately or with custom configurations. Defaults to `http://backbone-backend:8000` when using Docker Compose

## Quick Start with Docker Compose

The easiest way to run the application is using Docker Compose:

```bash
docker-compose up --build
```

This will:
- Build both the frontend and backend services
- Start the backend service first and wait for it to be healthy
- Start the frontend service only after the backend is ready
- Make the application available at http://localhost:7860

### Running Individual Services

To run only the backend:
```bash
docker-compose up backend
```

To run only the frontend:
```bash
docker-compose up frontend
```

## Accessing the Application

Once running, you can access:
- **Frontend (Gradio UI)**: http://localhost:7860
- **Backend API**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

The document processor provides the following endpoints:

### Health Check
- `GET /health` - Health check endpoint to verify the API is running
  - Returns: `{"status": "healthy", "service": "document_processor"}`

### PDF Processing
- `POST /process_pdf_file` - Process a PDF file and extract its content using unstructured
  - **Request**: Multipart form data with a PDF file
  - **Response**: 
    ```json
    {
      "status": "success",
      "content": "extracted text content...",
      "num_elements": 42,
      "file_size_mb": 1.23
    }
    ```

## Project Structure

```
├── document_processor.py      # FastAPI backend service
├── interface.py               # Gradio frontend interface
├── requirements.backend.txt   # Backend Python dependencies
├── requirements.frentend.txt  # Frontend Python dependencies
├── Dockerfile.backend         # Backend container definition
├── Dockerfile.frontend        # Frontend container definition
├── docker-compose.yml         # Multi-service setup
├── uploads/                   # File upload directory (mounted volume)
├── logs/                      # Application logs (mounted volume)
└── README.md
```

## Features

### Backend Service
- FastAPI-based REST API
- PDF processing using `unstructured` library
- Automatic text extraction from PDF documents
- Health check endpoint for service monitoring
- Comprehensive logging to `logs/document_processor.log`
- Temporary file cleanup after processing

### Frontend Service
- Gradio-based user interface
- PDF file upload and processing
- Real-time backend status indicator
- Automatic backend health checking
- Disabled UI until backend is ready
- Displays extracted content, element count, file size, and processing status

## Service Dependencies

The frontend service is configured to:
1. Wait for the backend to pass its health check before starting (via `depends_on` in docker-compose)
2. Perform additional health checks at startup (waits up to 60 seconds)
3. Disable UI components until backend is confirmed ready
4. Check backend health before processing each request

## Development

### Running Locally (without Docker)

#### Backend
```bash
pip install -r requirements.backend.txt
uvicorn document_processor:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
pip install -r requirements.frentend.txt
python interface.py
```

### Environment Variables

For detailed information about setting up environment variables, see the [Environment Variables Setup](#environment-variables-setup) section above.

All environment variables should be set in the `.env` file in the project root directory. The `docker-compose.yml` file automatically loads variables from the `.env` file.

### Logs

Backend logs are written to `logs/document_processor.log` with:
- Rotation: 100 MB per file
- Retention: 10 days
- Format: `{time} {level} {message}`
- Level: INFO

## Troubleshooting

### Backend not starting
- Check logs: `docker-compose logs backend`
- Verify health endpoint: `curl http://localhost:8000/health`
- Ensure port 8000 is not already in use

### Frontend not starting
- Check if backend is healthy first
- Check logs: `docker-compose logs frontend`
- Verify `BACKEND_URL` environment variable is set correctly

### PDF processing fails
- Ensure the uploaded file is a valid PDF
- Check backend logs for detailed error messages
- Verify unstructured library dependencies are installed correctly

## Debugging

To debug a container, you can access it with:

```bash
# Frontend container
docker exec -it backbone-frontend /bin/bash

# Backend container
docker exec -it backbone-backend /bin/bash
```

## License

See LICENSE file for details.
