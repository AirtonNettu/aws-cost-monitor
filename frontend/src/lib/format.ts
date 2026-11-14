export const DEFAULT_BRL_RATE = 5.75

export const money = (
  value: number,
  currency: 'USD' | 'BRL' = 'USD',
  rate = DEFAULT_BRL_RATE,
) => {
  const finalValue = currency === 'BRL' ? value * rate : value
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(finalValue)
}
export const percent = (value: number) =>
  `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1, signDisplay: 'exceptZero' }).format(value)}%`
export const date = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium',
    timeZone: 'UTC',
  }).format(new Date(`${value}T00:00:00Z`))
export const dateTime = (value: string) =>
  new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(value))
