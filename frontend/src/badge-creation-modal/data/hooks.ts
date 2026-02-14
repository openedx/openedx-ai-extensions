import { useCallback, useState } from 'react';
import type { BadgeFormData, GeneratedBadge } from '../types';
import * as badgeService from './api';

export interface UseGenerateBadgeResult {
  generate: (formData: BadgeFormData, courseId: string) => Promise<GeneratedBadge>;
  refine: (generatedBadge: GeneratedBadge, feedback: string, iteration: number) => Promise<GeneratedBadge>;
  save: (badge: GeneratedBadge, formData: BadgeFormData, courseId: string) => Promise<string>;
  isLoading: boolean;
  error: Error | null;
}
 
export const useGenerateBadge = (): UseGenerateBadgeResult => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const generate = useCallback(async (formData: BadgeFormData, courseId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const badge = await badgeService.generateBadge({ formData, courseId });
      return badge;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refine = useCallback(async (generatedBadge: GeneratedBadge, feedback: string, iteration: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const badge = await badgeService.refineBadge({ generatedBadge, feedback, iteration });
      return badge;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const save = useCallback(async (badge: GeneratedBadge, formData: BadgeFormData, courseId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const filePath = await badgeService.saveBadge({ badge, badgeData: formData, courseId });
      return filePath;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    generate,
    refine,
    save,
    isLoading,
    error,
  };
}

export default useGenerateBadge;