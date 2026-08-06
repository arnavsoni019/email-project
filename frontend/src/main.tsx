import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './tokens.css' // design tokens, extracted verbatim from the Aurora Pro design file
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
