import { render, screen, fireEvent } from '@testing-library/react';
import { Dropdown } from '../dropdown';
import { expect, test, vi } from 'vitest';

const options = [
  { value: '1', label: 'Option 1' },
  { value: '2', label: 'Option 2' },
];

test('renders dropdown with label and options', () => {
  render(<Dropdown options={options} label="Choose option" value="1" />);
  expect(screen.getByText('Choose option')).toBeInTheDocument();
  expect(screen.getByRole('combobox')).toHaveValue('1');
});

test('handles option change', () => {
  const handleChange = vi.fn();
  render(<Dropdown options={options} label="Choose option" value="1" onChange={handleChange} />);
  const select = screen.getByRole('combobox');
  fireEvent.change(select, { target: { value: '2' } });
  expect(handleChange).toHaveBeenCalledWith('2');
});
