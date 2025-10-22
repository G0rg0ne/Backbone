# Backbone

Dynamic Summarization of Scientific Papers Using Profile-Aware AI 


## Prerequisites

- Docker installed on your system
- Git (to clone the repository)

## Running with Docker

### Building the Docker Image

To build the Docker image, run the following command in the project root directory:

```bash
docker build -t backbone .
```

This will:
- Create a Docker image named `backbone`
- Install all Python dependencies from `requirements.txt`
- Set up the Reflex environment
- Copy your application code into the container

### Running the Container

To run the container with the current directory mounted for development:

```bash
docker run -it --rm -p 3000:3000 -p 8000:8000 -v $(pwd):/app backbone /bin/bash
```

### What the Docker Run Command Does

- `-it`: Runs the container in interactive mode with a TTY
- `--rm`: Automatically removes the container when it exits
- `-p 3000:3000`: Maps port 3000 from the container to port 3000 on your host (frontend)
- `-p 8000:8000`: Maps port 8000 from the container to port 8000 on your host (backend)
- `-v $(pwd):/app`: Mounts the current directory to `/app` in the container for live development
- `backbone`: The name of the Docker image to run
- `/bin/bash`: Starts a bash shell inside the container

### Accessing the Application

Once the container is running, you can access:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

### Development Mode

With the current directory mounted, any changes you make to your Python files will be reflected in the running container. Once inside the container, you can run your Reflex app with:

```bash
reflex run --backend-host 0.0.0.0 --backend-port 8000 --frontend-port 3000
```

### Stopping the Container

To stop the running container, press `Ctrl+C` in the terminal where it's running, or find the container ID and stop it:

```bash
docker ps
docker stop <container_id>


## Project Structure

- `app.py`: Main Reflex application code
- `requirements.txt`: Python dependencies
- `Dockerfile`: Docker configuration
- `uploads/`: Directory for file uploads (if needed)

## Run the REFLEX app using :

```bash
reflex run --backend-host 0.0.0.0 --backend-port 8000 --frontend-port 3000
```