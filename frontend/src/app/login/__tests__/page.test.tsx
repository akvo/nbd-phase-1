import { render, screen, fireEvent } from '@testing-library/react';
import LoginPage from '../page';
import { expect, test, vi } from 'vitest';

// Mock alert to prevent runtime errors in tests
global.alert = vi.fn();

test('renders login page elements and validations', () => {
  render(<LoginPage />);

  expect(screen.getByText('Log in to your account')).toBeInTheDocument();

  const emailInput = screen.getByPlaceholderText('Enter your email');
  const passwordInput = screen.getByPlaceholderText('Password');
  const signInButton = screen.getByRole('button', { name: /^sign in$/i });

  // Test empty validation
  fireEvent.click(signInButton);
  expect(screen.getByText('Please fill in all fields.')).toBeInTheDocument();

  // Test invalid email format
  fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });
  fireEvent.click(signInButton);
  expect(screen.getByText('Please enter a valid email address.')).toBeInTheDocument();

  // Test successful submission triggers alert
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.click(signInButton);
  expect(global.alert).toHaveBeenCalled();
});
