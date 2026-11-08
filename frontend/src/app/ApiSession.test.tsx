import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { ApiSession } from './ApiSession'

it('autentica na API sem persistir credenciais no navegador', async () => {
  const user = userEvent.setup()
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (_url, init) => {
      if (!new Headers(init?.headers).has('Authorization'))
        return new Response('{}', { status: 401 })
      return new Response(JSON.stringify({ runs: [] }))
    })
  render(
    <MemoryRouter initialEntries={['/history']}>
      <ApiSession base="/api/v1" />
    </MemoryRouter>,
  )
  await user.type(screen.getByLabelText('Usuário'), 'operator')
  await user.type(
    screen.getByLabelText('Senha'),
    'credencial-sintetica-de-teste',
  )
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
  expect(await screen.findByText('Nenhuma análise salva')).toBeInTheDocument()
  expect(fetcher).toHaveBeenCalled()
  expect(localStorage.getItem('Authorization')).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Sair da API' }))
  expect(screen.getByLabelText('Senha')).toHaveValue('')
})
