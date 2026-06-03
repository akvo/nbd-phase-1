import { render, screen } from '@testing-library/react';
import { Card, CardHeader, CardTitle, CardDescription, CardAction, CardContent, CardFooter } from '../card';
import { expect, test } from 'vitest';

test('renders card subcomponents correctly', () => {
  render(
    <Card size="sm">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
        <CardDescription>Card Description</CardDescription>
        <CardAction>Card Action</CardAction>
      </CardHeader>
      <CardContent>Card Content</CardContent>
      <CardFooter>Card Footer</CardFooter>
    </Card>
  );

  expect(screen.getByText('Card Title')).toBeInTheDocument();
  expect(screen.getByText('Card Description')).toBeInTheDocument();
  expect(screen.getByText('Card Action')).toBeInTheDocument();
  expect(screen.getByText('Card Content')).toBeInTheDocument();
  expect(screen.getByText('Card Footer')).toBeInTheDocument();

  expect(screen.getByText('Card Title').parentElement).toHaveAttribute('data-slot', 'card-header');
});
