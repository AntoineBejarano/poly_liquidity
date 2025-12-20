import type { Meta, StoryObj } from '@storybook/react';
import { CustomChartTooltip } from './CustomChartTooltip';

const meta: Meta<typeof CustomChartTooltip> = {
  title: 'Charts/CustomChartTooltip',
  component: CustomChartTooltip,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof CustomChartTooltip>;

export const Default: Story = {
  args: {
    active: true,
    payload: [
      {
        name: 'Equity',
        value: 125000,
        color: 'hsl(var(--chart-1))',
        dataKey: 'equity',
      },
    ],
    label: '2024-01-15',
    valueFormatter: (value: number) => `$${value.toLocaleString()}`,
  },
};

export const MultipleSeries: Story = {
  args: {
    active: true,
    payload: [
      {
        name: 'Equity',
        value: 125000,
        color: 'hsl(var(--chart-1))',
        dataKey: 'equity',
      },
      {
        name: 'PnL',
        value: 5000,
        color: 'hsl(var(--chart-2))',
        dataKey: 'pnl',
      },
    ],
    label: '2024-01-15',
    valueFormatter: (value: number) => `$${value.toLocaleString()}`,
  },
};

export const Inactive: Story = {
  args: {
    active: false,
    payload: [],
    label: '',
  },
};

