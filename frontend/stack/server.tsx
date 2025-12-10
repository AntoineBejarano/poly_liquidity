import { StackServerApp } from '@stackframe/stack';
import { stackClientApp } from './client';

const stackSecretServerKey = process.env.STACK_SECRET_SERVER_KEY;

if (!stackSecretServerKey) {
  throw new Error('Missing STACK_SECRET_SERVER_KEY environment variable');
}

export const stackServerApp = new StackServerApp({
  inheritsFrom: stackClientApp,
  secretServerKey: stackSecretServerKey,
});

