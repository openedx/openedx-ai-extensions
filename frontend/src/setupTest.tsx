/* eslint-disable import/no-extraneous-dependencies */
import '@testing-library/jest-dom';
import { ReactNode } from 'react';
import { render } from '@testing-library/react';
import { IntlProvider } from '@edx/frontend-platform/i18n';

interface WrapperProps {
  children: ReactNode;
}

export const renderWrapper = (ui, options = {}) => {
  const Wrapper = ({ children }: WrapperProps) => (
    <IntlProvider locale="en">{children}</IntlProvider>
  );

  return render(ui, { wrapper: Wrapper, ...options });
};

class ResizeObserver {
  observe() { }

  unobserve() { }

  disconnect() { }
}

global.ResizeObserver = ResizeObserver;
