UI Kit (minimal) - components/ui

Included components:
- `Button` - props: `variant: 'primary' | 'secondary'`, forwards `className` and native button props.
- `Input` - simple labelled input, supports standard input props.
- `Card` - container with `compact` option.

Usage examples:

import { Button, Input, Card } from '@/components/ui';

<Button variant="primary" onClick={() => {}}>Guardar</Button>

<Card>
  <h3>Resumen</h3>
  <p>Contenido</p>
</Card>

Notes:
- These wrap existing CSS tokens present in `app/globals.css` (classes: `btn`, `btn-primary`, `input`, `card`).
- Plan: migrate these to shadcn variants and document with Storybook.
