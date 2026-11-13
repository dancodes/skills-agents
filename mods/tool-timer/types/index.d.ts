export type TookMs = number

declare module 'claude-code' {
  interface PluginState {
    'tool-timer': { tookMs: StateFamily<TookMs> }
  }
}
