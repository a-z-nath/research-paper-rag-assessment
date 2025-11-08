# Research Paper RAG System - Frontend

A clean Next.js + TypeScript + Tailwind CSS frontend to interact with the Research Paper RAG backend API.

## Features

- 📄 **Upload Papers** - Upload PDF research papers
- 📚 **View All Papers** - Browse uploaded papers with metadata
- 🔍 **Query Papers** - Ask questions and get AI-powered answers with citations
- 📊 **Query History** - Review past queries and their results

## Setup

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The app will be available at **http://localhost:3000**

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with navigation
│   ├── page.tsx            # Home page
│   ├── upload/page.tsx     # Upload papers
│   ├── papers/page.tsx     # List all papers
│   ├── query/page.tsx      # Query interface
│   └── history/page.tsx    # Query history
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js          # API proxy config
```

## API Integration

The frontend connects to the backend via:
- Direct fetch to `http://localhost:8000/api/*`
- Configured proxy in `next.config.js` (optional)

## Available Scripts

```powershell
npm run dev      # Start development server
npm run build    # Build for production
npm start        # Start production server
npm run lint     # Run ESLint
```

## Usage

1. **Upload Papers**
   - Go to `/upload`
   - Select PDF file
   - Wait for processing (first upload may take longer)

2. **View Papers**
   - Go to `/papers`
   - See all uploaded papers with metadata
   - Delete papers if needed

3. **Query**
   - Go to `/query`
   - Ask a question
   - Adjust top_k slider for more/fewer results
   - View answer with citations

4. **History**
   - Go to `/history`
   - Review past queries
   - See confidence scores and response times

## Tech Stack

- **Next.js 14** (App Router)
- **React 18**
- **TypeScript**
- **Tailwind CSS**
- **Fetch API** for backend communication

## Troubleshooting

### Backend connection issues
- Ensure backend is running on http://localhost:8000
- Check CORS settings in backend (already configured)

### Port conflicts
- Change dev port: `npm run dev -- -p 3001`

### Build errors
- Clear cache: `rm -rf .next node_modules && npm install`

## Notes

- Lint errors before `npm install` are normal
- The API proxy in next.config.js is optional; direct fetch works fine
- Tailwind warnings in CSS files are expected
