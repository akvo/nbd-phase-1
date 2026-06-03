import { render } from '@testing-library/react';
import { EChartsChart } from '../echarts-chart';
import { expect, test, vi } from 'vitest';
import * as echarts from 'echarts';

vi.mock('echarts', () => {
  const mockChart = {
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
  };
  return {
    init: vi.fn(() => mockChart),
  };
});

test('renders container and initializes chart', () => {
  const options = { title: { text: 'Test Chart' } };
  const { container } = render(<EChartsChart options={options} className="custom-chart" />);
  expect(container.firstChild).toBeInTheDocument();
  expect(echarts.init).toHaveBeenCalled();
});
