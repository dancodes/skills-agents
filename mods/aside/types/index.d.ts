export type AsideEntry = { kind: 'question' | 'answer' | 'tool'; text: string }

export type Aside = {
  forkId: string | null
  entries: AsideEntry[]
  isBusy: boolean
  isConfirming: boolean
  error: string | null
}

declare module 'claude-code' {
  interface PluginState {
    aside: { aside: Aside }
  }
}
