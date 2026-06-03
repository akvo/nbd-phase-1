import { render, screen } from '@testing-library/react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../table';
import { expect, test } from 'vitest';

test('renders table structure correctly with headers and cells', () => {
  render(
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Header 1</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell>Cell 1</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );

  expect(screen.getByText('Header 1')).toBeInTheDocument();
  expect(screen.getByText('Cell 1')).toBeInTheDocument();
});
