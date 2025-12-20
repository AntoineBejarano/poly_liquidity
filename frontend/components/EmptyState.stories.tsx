import type { Meta, StoryObj } from '@storybook/react';
import { EmptyState } from './EmptyState';
import { LineChart, TrendingUp, AlertCircle } from 'lucide-react';

const meta: Meta<typeof EmptyState> = {
  title: 'Components/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const Default: Story = {
  args: {
    icon: LineChart,
    title: 'No strategies yet',
    description: 'Create your first algorithmic trading strategy to get started with automated trading.',
    action: {
      label: 'Create Strategy',
      onClick: () => console.log('Create clicked'),
    },
  },
};

export const WithoutAction: Story = {
  args: {
    icon: TrendingUp,
    title: 'No data available',
    description: 'There is no data to display at the moment.',
  },
};

export const WithError: Story = {
  args: {
    icon: AlertCircle,
    title: 'Error loading data',
    description: 'Something went wrong while loading the data. Please try again later.',
    action: {
      label: 'Retry',
      onClick: () => console.log('Retry clicked'),
    },
  },
};

