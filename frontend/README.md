# Medicare AI Chatbot - Frontend

Modern, responsive chatbot interface built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

- 🎨 **Clean, Familiar UI**: ChatGPT-style interface that users know and love
- 🌍 **Multi-language Support**: Ask in English or Korean (한국어) - responses match your language
- 📱 **Fully Responsive**: Works seamlessly on mobile, tablet, and desktop
- ⚡ **Real-time Streaming**: SSE-based streaming for live response generation
- 📚 **Citation Display**: Clear source references with section and page numbers
- 🎯 **Confidence Indicators**: Visual indicators for answer confidence levels
- ♿ **Accessible**: Built with accessibility best practices
- 🎭 **Example Questions**: Quick-start suggestions for users in both languages

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **State Management**: React Hooks

## Getting Started

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Set Up Environment

Create a `.env.local` file:

```bash
cp .env.local.example .env.local
```

Update the API URL if needed:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Start Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   └── globals.css        # Global styles
│   ├── components/            # React components
│   │   ├── ChatInterface.tsx  # Main chat container
│   │   ├── MessageBubble.tsx  # Message display
│   │   ├── CitationList.tsx   # Citation display
│   │   └── ChatInput.tsx      # Input area
│   ├── lib/                   # Utilities
│   │   ├── api.ts            # API client
│   │   └── utils.ts          # Helper functions
│   └── types/                # TypeScript types
│       └── chat.ts           # Chat-related types
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## Components

### ChatInterface

Main container component that orchestrates the entire chat experience.

**Features:**
- Message state management
- API communication with streaming support
- Error handling
- Auto-scrolling

### MessageBubble

Individual message display component.

**Features:**
- User vs assistant styling
- Citation display
- Confidence indicators
- Streaming animation
- Disclaimer for assistant messages

### CitationList

Displays source citations for answers.

**Features:**
- Expandable list
- Section and page information
- Document version tracking
- Click-through capability (future enhancement)

### ChatInput

Message input component with auto-resize.

**Features:**
- Auto-expanding textarea
- Example questions
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)
- Loading states
- Character limit (future enhancement)

## API Integration

The frontend communicates with the FastAPI backend through the API client in `src/lib/api.ts`.

### Endpoints Used

- `POST /api/v1/agent/chat` - Send messages and receive responses
- `GET /api/v1/health` - Health check

### Streaming Support

The frontend uses Server-Sent Events (SSE) to stream responses in real-time:

```typescript
for await (const chunk of apiClient.chatStream(request)) {
  // Update UI with each chunk
}
```

## Responsive Design

The interface adapts to different screen sizes:

- **Mobile (<640px)**: Single column, full-width messages
- **Tablet (640px-1024px)**: Optimized spacing and layout
- **Desktop (>1024px)**: Maximum width container for comfortable reading

## Customization

### Colors

Edit `tailwind.config.js` to customize the color scheme:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your custom colors
      },
    },
  },
}
```

### Message Styling

Modify `MessageBubble.tsx` to change message appearance:

```typescript
className={`rounded-2xl px-4 py-3 ${
  isUser ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-900'
}`}
```

## Building for Production

### Build

```bash
npm run build
```

### Start Production Server

```bash
npm start
```

### Deploy

The app can be deployed to:
- **Vercel**: `vercel deploy`
- **Netlify**: Connect your Git repository
- **Docker**: Use the included Dockerfile (if available)
- **Static Export**: Set `output: 'export'` in next.config.js

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Accessibility

- Semantic HTML elements
- ARIA labels where appropriate
- Keyboard navigation support
- Screen reader friendly

## Performance

- Server-side rendering (SSR) with Next.js
- Automatic code splitting
- Optimized bundle size
- Efficient re-renders with React hooks

## Future Enhancements

- [ ] Conversation history persistence
- [ ] Dark mode toggle
- [ ] Voice input support
- [ ] PDF viewer for citations
- [ ] Multi-language support
- [ ] Export conversation to PDF
- [ ] Share conversation links
- [ ] User authentication

## Troubleshooting

### API Connection Issues

If the frontend can't connect to the backend:

1. Ensure the backend is running on http://localhost:8000
2. Check CORS settings in the backend
3. Verify `NEXT_PUBLIC_API_URL` in `.env.local`

### Streaming Not Working

1. Ensure the backend supports SSE
2. Check browser console for errors
3. Verify the API endpoint returns proper SSE format

### Build Errors

1. Clear `.next` folder: `rm -rf .next`
2. Clear node_modules: `rm -rf node_modules && npm install`
3. Check TypeScript errors: `npm run lint`

## License

[Same as parent project]
