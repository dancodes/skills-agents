import { expect, test } from 'claude-code/testing'

import { usageParts } from '../hooks/format'

test('splits 5h and weekly usage into label, percent and time to reset', async () => {
  const now = Date.parse('2026-10-13T10:00:00Z')
  const limits = [
    { kind: 'five_hour', percentUsed: 23.5, resetsAt: '2026-10-13T12:10:00Z' },
    { kind: 'seven_day', percentUsed: 41, resetsAt: '2026-10-16T13:00:00Z' },
    { kind: 'spend_limit', percentUsed: 5 },
  ]

  expect(usageParts(limits, now)).toEqual([
    { label: '5h', percent: '23.5%', reset: '2h10m' },
    { label: 'wk', percent: '41%', reset: '3d3h' },
  ])
  expect(usageParts([{ kind: 'five_hour', percentUsed: 7 }], now)).toEqual([{ label: '5h', percent: '7%', reset: null }])
  expect(usageParts([], now)).toEqual([])
})
