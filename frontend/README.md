# Manim GPT - Frontend

A modern React + Tailwind CSS UI for the Manim GPT animation generator.

## Features

- **Real-time Code Generation**: Stream iterative code generation with live progress updates
- **Interactive Code Editor**: View and edit generated Manim code with syntax highlighting
- **LLM Model Selection**: Choose from 100+ LLM providers and models
- **Video Rendering**: Render animations in multiple formats (MP4, WebM, GIF, MOV) and qualities
- **Iteration Tracking**: View detailed history of code generation iterations
- **Validation Feedback**: Real-time code validation with error and warning display

## Tech Stack

- **React 19**: Modern React with hooks
- **Vite**: Lightning-fast development and building
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icon library
- **React Syntax Highlighter**: Code syntax highlighting

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Environment Variables

Create a `.env` file with the following:

```env
VITE_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── GenerationForm.jsx
│   │   ├── CodeEditor.jsx
│   │   ├── ProgressView.jsx
│   │   ├── IterationLogs.jsx
│   │   ├── RenderSettings.jsx
│   │   ├── VideoPlayer.jsx
│   │   └── ModelSelector.jsx
│   ├── services/
│   │   └── api.js           # API client
│   ├── App.jsx              # Main app component
│   └── index.css            # Tailwind styles
├── tailwind.config.js
└── vite.config.js
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## API Integration

The frontend communicates with the FastAPI backend using:

- **REST endpoints** for standard operations
- **Server-Sent Events (SSE)** for real-time streaming updates during code generation

Key API endpoints:
- `POST /session/generate-stream` - Stream code generation with SSE
- `GET /session/status/{session_id}` - Get session status
- `POST /session/update-code` - Update and validate code
- `POST /session/render` - Render video
- `GET /models/providers` - List LLM providers

## Development

The app uses Vite's Hot Module Replacement (HMR) for instant updates during development.

## Building for Production

```bash
npm run build
```

The production-ready files will be in the `dist/` directory.
