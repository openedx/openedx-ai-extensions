import React, { createContext, useContext } from 'react';
import { UseLibraryCreatorReturn } from '../hooks/useLibraryCreator';

interface LibraryCreatorContextValue extends UseLibraryCreatorReturn {
  // Library picker state
  libraries: Array<{ id: string; title: string }>;
  selectedLibrary: string;
  libraryError: string;
  isLoadingLibraries: boolean;
  setSelectedLibrary: (lib: string) => void;
  setLibraryError: (err: string) => void;
  // Derived / handlers owned by LibraryComponentCreator
  activeCount: number;
  handleSave: () => void;
  handleStartOver: () => void;
  // Modal
  isOpen: boolean;
  close: () => void;
  /** Optional external code-editor component (e.g. Monaco, CodeMirror) for OLX editing */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  CodeEditor?: React.ComponentType<any> | null;
}

const LibraryCreatorContext = createContext<LibraryCreatorContextValue | null>(null);

export const LibraryCreatorProvider = ({
  children,
  value,
}: {
  children: React.ReactNode;
  value: LibraryCreatorContextValue;
}) => (
  <LibraryCreatorContext.Provider value={value}>
    {children}
  </LibraryCreatorContext.Provider>
);

export const useLibraryCreatorContext = (): LibraryCreatorContextValue => {
  const ctx = useContext(LibraryCreatorContext);
  if (!ctx) {
    throw new Error('useLibraryCreatorContext must be used inside LibraryCreatorProvider');
  }
  return ctx;
};
