'use client';

import { StackClientApp } from '@stackframe/stack';

const stackProjectId = process.env.NEXT_PUBLIC_STACK_PROJECT_ID;
const stackPublishableClientKey = process.env.NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY;

if (!stackProjectId || !stackPublishableClientKey) {
  throw new Error('Missing Stack OAuth environment variables. Please set NEXT_PUBLIC_STACK_PROJECT_ID and NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY in .env.local');
}

export const stackClientApp = new StackClientApp({
  projectId: stackProjectId,
  publishableClientKey: stackPublishableClientKey,
  tokenStore: "nextjs-cookie",
  urls: {
    signIn: "/sign-in",
    signUp: "/sign-up",
    afterSignIn: "/dashboard",
    afterSignOut: "/",
  },
});

