# ISEA v2.0 - UI & Performance Upgrade

## New Features
- **3D Neural Interface**: A stunning, interactive 3D particle system built with Three.js and React Three Fiber, visualizing the agent's "neural activity".
- **Glassmorphism Design**: High-end UI with backdrop blurs, gradients, and semantic coloring for different agent modes (Quick, Research, Explain).
- **Real-Time Streaming**: The backend now streams execution steps immediately to the frontend. No more "Processing..." spinner for 20 seconds. You see the agent thinking in real-time.
- **Enhanced Performance**: 
  - Reduced retry latencies.
  - Optimized for `gemini-1.5-flash`.
  - Removed artificial frontend delays.

## How to Run
1. **Backend**:
   ```bash
   python api.py
   ```
2. **Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000).

## Troubleshooting
- If the 3D background is black, ensure hardware acceleration is enabled in your browser.
- If the agent seems stuck or "just stops" without replying:
  - Check your terminal. If you see `Retrying langchain_google_genai...` or `404 NOT_FOUND`, your **Google API Key** is invalid or lacks permissions.
  - **SOLUTION**: Go to [Google AI Studio](https://aistudio.google.com/), create a **new API specific key** (using "Create in a new project" is recommended), and update `.env`.
  - Restart the backend (`python api.py`).
