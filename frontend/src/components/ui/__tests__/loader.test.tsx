import { render, screen } from '@testing-library/react';
import { Loader } from '../loader';
import { expect, test } from 'vitest';

test('renders loader with default message', () => {
  render(<Loader />);
  expect(screen.getByText('Loading...')).toBeInTheDocument();
});

test('renders loader with custom message', () => {
  render(<Loader message="Processing data..." />);
  expect(screen.getByText('Processing data...')).toBeInTheDocument();
});
