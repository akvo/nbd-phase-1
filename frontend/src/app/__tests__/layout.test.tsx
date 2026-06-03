import { render, screen } from '@testing-library/react';
import RootLayout from '../layout';
import { expect, test } from 'vitest';

test('renders root layout with children', () => {
  render(
    <RootLayout>
      <div data-testid="layout-child">Child Element</div>
    </RootLayout>
  );

  expect(screen.getByTestId('layout-child')).toBeInTheDocument();
  expect(screen.getByText('Child Element')).toBeInTheDocument();
});
