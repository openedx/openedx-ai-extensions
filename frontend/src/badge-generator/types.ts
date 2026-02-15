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
