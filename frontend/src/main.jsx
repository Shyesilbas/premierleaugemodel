import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { syncDataVersion } from './utils/teamProfileCache'

// Check before the first render so no tab reads a cache made from data the API has since replaced.
syncDataVersion().finally(() => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})

// A tab left open while new data is synced picks it up when the user comes back to it.
document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'visible' && await syncDataVersion()) window.location.reload()
})
