import { render, screen } from '@testing-library/react';
import { MessageNote } from '../message-note';
import { expect, test } from 'vitest';

test('renders message note with title and content', () => {
  render(
    <MessageNote type="success" title="Success Title">
      Success Content Message
    </MessageNote>
  );

  expect(screen.getByText('Success Title')).toBeInTheDocument();
  expect(screen.getByText('Success Content Message')).toBeInTheDocument();
});

test('applies type styles correctly', () => {
  const { container: containerInfo } = render(<MessageNote type="info" />);
  expect(containerInfo.firstChild).toHaveClass('border-nbd-primary');

  const { container: containerError } = render(<MessageNote type="error" />);
  expect(containerError.firstChild).toHaveClass('border-red-500');

  const { container: containerWarning } = render(<MessageNote type="warning" />);
  expect(containerWarning.firstChild).toHaveClass('border-yellow-500');
});
