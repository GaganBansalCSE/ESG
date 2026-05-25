import { render, screen } from '@testing-library/react';
import App from './App';

test('renders ESG Data Ingestion Platform header', () => {
  render(<App />);
  const headerElement = screen.getByText(/ESG|ingestion|data/i);
  expect(headerElement).toBeInTheDocument();
});
