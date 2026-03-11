import { render, RenderOptions } from '@testing-library/react'
import { MemoryRouter, MemoryRouterProps } from 'react-router-dom'
import { ReactElement } from 'react'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  routerProps?: MemoryRouterProps
}

function AllProviders({ children, routerProps }: { children: React.ReactNode; routerProps?: MemoryRouterProps }) {
  return <MemoryRouter {...routerProps}>{children}</MemoryRouter>
}

export function renderWithProviders(ui: ReactElement, options: CustomRenderOptions = {}) {
  const { routerProps, ...renderOptions } = options

  return render(ui, {
    wrapper: ({ children }) => <AllProviders routerProps={routerProps}>{children}</AllProviders>,
    ...renderOptions,
  })
}

export { renderWithProviders as customRender }
