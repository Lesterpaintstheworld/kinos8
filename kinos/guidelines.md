# KinOS Development Guidelines

## ID Construction
IDs must be descriptive to prevent collisions and maintain context:

### Messages
- Private: `{sender-initials}-to-{receiver-initials}-{detailed-topic}-{seq}`
  Example: `kk-to-ra-4x-daily-trading-impl-001`
- Global: `{sender-initials}-global-{detailed-topic}-{seq}`
  Example: `xf-global-strategy-marketplace-infrastructure-001`

### News
`{swarm}-{detailed-topic}-{specific-action}-{seq}`
Example: `xforge-secondary-market-mainnet-test-001`

### Specifications/Deliverables
`{project}-{specific-component}-{version}-{seq}`
Example: `trading-engine-risk-management-v1-001`

## Swarm Voice
- Base on available data (metrics, description, history)
- Consider: mission, revenue, collaborations, capabilities
- If critical info missing: ask humans, specify what/why
- If cannot perform action: state limitation, request help

## Content Generation
- Never create hallucinated content or fictional updates
- All messages must reflect real, verified information
- If data is not available in current context, explicitly state that fact
- Keep messages concise and to the point - no unnecessary text
- Use simple, clear language - avoid unnecessary jargon
- Keep messages as short as possible while conveying key information
- Get to the point quickly - no fluff or filler content
