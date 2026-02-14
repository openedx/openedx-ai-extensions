/**
 * Types for Badge Creation Modal workflow
 */

export type BadgeScope = 'course' | 'section' | 'unit';
export type BadgeStyle = 'modern' | 'classic' | 'minimalist' | 'playful';
export type BadgeTone = 'professional' | 'friendly' | 'academic' | 'creative';
export type BadgeLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type BadgeCriterion = 'completion' | 'mastery' | 'participation' | 'excellence';

export interface BadgeFormData {
  scope: BadgeScope;
  unitId?: string;
  style: BadgeStyle;
  tone: BadgeTone;
  level: BadgeLevel;
  criterion: BadgeCriterion;
  skillsEnabled: boolean;
  description?: string;
}

export interface GeneratedBadge {
  id: string;
  title: string;
  description: string;
  image: string; // SVG or image data URL
  metadata?: Record<string, any>;
}

export interface FeedbackEntry {
  iteration: number;
  feedback: string;
  timestamp: string;
  generatedBadge?: GeneratedBadge;
}

export interface BadgeCreationSession {
  courseId: string;
  courseName?: string;
  sessionId: string;
  formData: BadgeFormData;
  generatedBadges: GeneratedBadge[];
  feedbackHistory: FeedbackEntry[];
  currentIteration: number;
  status: 'initial' | 'generating' | 'reviewing' | 'saving' | 'completed' | 'error';
  error?: string;
  createdAt: string;
  lastModified: string;
}

/**
 * Workflow state for orchestrating steps
 */
export type WorkflowStep = 'input_form' | 'generating' | 'preview' | 'feedback' | 'saving' | 'complete';

export interface WorkflowState {
  currentStep: WorkflowStep;
  formData: BadgeFormData;
  currentBadge: GeneratedBadge | null;
  feedbackHistory: FeedbackEntry[];
  isLoading: boolean;
  error: string | null;
  saveSuccess: boolean;
  iterationCount: number;
}

/**
 * Human-in-Loop metrics for analysis
 */
export interface HumanInLoopMetrics {
  totalSessions: number;
  totalIterations: number;
  averageIterationsPerBadge: number;
  feedbackPatterns: Record<string, number>;
  commonRefinements: string[];
  averageTimePerSession: number;
  acceptanceRate: number; // badges saved / total generated
}
