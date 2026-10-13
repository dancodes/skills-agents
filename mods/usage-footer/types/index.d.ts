export type Limits = readonly { kind: string; percentUsed: number; resetsAt?: string }[]

declare module 'claude-code' {
  interface PluginState {
    'usage-footer': { limits: Limits }
  }
}
