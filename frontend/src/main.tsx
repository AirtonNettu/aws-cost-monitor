import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './app/App'
import { createDataClient } from './api/client'
import './styles.css'

const root = createRoot(document.getElementById('root')!)
createDataClient()
  .then((client) =>
    root.render(
      <StrictMode>
        <BrowserRouter>
          <App client={client} />
        </BrowserRouter>
      </StrictMode>,
    ),
  )
  .catch(() => {
    root.render(
      <main className="bootstrap-error">
        <h1>Configuração inválida</h1>
        <p>
          Confira VITE_DATA_MODE e VITE_MOCK_SCENARIO nas configurações do
          frontend e reinicie o servidor.
        </p>
      </main>,
    )
  })
