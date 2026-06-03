import { render } from '@testing-library/react';
import { Progress } from '../progress';
import { expect, test } from 'vitest';

test('renders progress bar with value', () => {
  const { container } = render(<Progress value={45} />);
  const progressBar = container.firstChild as HTMLElement;
  expect(progressBar).toBeInTheDocument();

  const indicator = progressBar.firstChild as HTMLElement;
  expect(indicator.style.transform).toBe('translateX(-55%)');
});

test('clamps progress value between 0 and 100', () => {
  const { container: containerMin } = render(<Progress value={-10} />);
  const indicatorMin = containerMin.firstChild?.firstChild as HTMLElement;
  expect(indicatorMin.style.transform).toBe('translateX(-100%)');

  const { container: containerMax } = render(<Progress value={150} />);
  const indicatorMax = containerMax.firstChild?.firstChild as HTMLElement;
  expect(indicatorMax.style.transform).toBe('translateX(-0%)');
});
