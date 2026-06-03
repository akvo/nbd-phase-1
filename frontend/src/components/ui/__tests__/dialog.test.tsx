import { render, screen } from '@testing-library/react';
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../dialog';
import { expect, test } from 'vitest';

test('renders open dialog content', () => {
  render(
    <Dialog open={true}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>Dialog Description</DialogDescription>
        </DialogHeader>
        <div>Content</div>
        <DialogFooter>
          <button>Confirm</button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  expect(screen.getByText('Dialog Title')).toBeInTheDocument();
  expect(screen.getByText('Dialog Description')).toBeInTheDocument();
  expect(screen.getByText('Content')).toBeInTheDocument();
  expect(screen.getByText('Confirm')).toBeInTheDocument();
});
