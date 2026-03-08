import React, { createContext, useContext } from 'react';
import { UseLibraryCreatorReturn } from '../hooks/useLibraryProblemCreator';

interface LibraryProblemCreatorContextValue extends UseLibraryCreatorReturn {
  // Library picker state
  libraries: Array<{ id: string; title: string }>;
  selectedLibrary: string;
  libraryError: string;
  isLoadingLibraries: boolean;
  setSelectedLibrary: (lib: string) => void;
  setLibraryError: (err: string) => void;
  // Derived / handlers owned by LibraryProblemCreator
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

const LibraryProblemCreatorContext = createContext<LibraryProblemCreatorContextValue | null>(null);

export const LibraryProblemCreatorProvider = ({
  children,
  value,
}: {
  children: React.ReactNode;
  value: LibraryProblemCreatorContextValue;
}) => (
  <LibraryProblemCreatorContext.Provider value={value}>
    {children}
  </LibraryProblemCreatorContext.Provider>
);

export const useLibraryProblemCreatorContext = (): LibraryProblemCreatorContextValue => {
  const ctx = useContext(LibraryProblemCreatorContext);
  if (!ctx) {
    throw new Error('useLibraryProblemCreatorContext must be used inside LibraryProblemCreatorProvider');
  }
  return ctx;
};
