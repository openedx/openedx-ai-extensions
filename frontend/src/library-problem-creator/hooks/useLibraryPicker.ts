import { useState, useCallback } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logError } from '@edx/frontend-platform/logging';
import { fetchLibrariesApi, Library } from '../data/library';
import messages from '../messages';

export interface UseLibraryPickerReturn {
  libraries: Library[];
  selectedLibrary: string;
  libraryError: string;
  isLoadingLibraries: boolean;
  setSelectedLibrary: (lib: string) => void;
  setLibraryError: (err: string) => void;
  fetchLibraries: () => Promise<void>;
}

export function useLibraryPicker(): UseLibraryPickerReturn {
  const intl = useIntl();

  const [libraries, setLibraries] = useState<Library[]>([]);
  const [selectedLibrary, setSelectedLibrary] = useState('');
  const [isLoadingLibraries, setIsLoadingLibraries] = useState(false);
  const [librariesFetched, setLibrariesFetched] = useState(false);
  const [libraryError, setLibraryError] = useState('');

  const fetchLibraries = useCallback(async () => {
    if (librariesFetched) { return; }
    setIsLoadingLibraries(true);
    setLibraryError('');
    try {
      const fetched = await fetchLibrariesApi();
      setLibraries(fetched);
      setLibrariesFetched(true);
    } catch (err) {
      logError('useLibraryPicker: failed to fetch libraries:', err);
      setLibraryError(intl.formatMessage(messages['ai.library.creator.library.error']));
    } finally {
      setIsLoadingLibraries(false);
    }
  }, [librariesFetched, intl]);

  return {
    libraries,
    selectedLibrary,
    libraryError,
    isLoadingLibraries,
    setSelectedLibrary,
    setLibraryError,
    fetchLibraries,
  };
}
