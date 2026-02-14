/**
 * Badge service for handling badge generation and saving
 * This is a POC implementation with mock API calls that can be replaced
 * with actual backend API calls in production
 */

import { BadgeFormData, GeneratedBadge } from '../types';

interface BadgeGenerationRequest {
  formData: BadgeFormData;
  courseId: string;
}

interface BadgeRefinementRequest {
  generatedBadge: GeneratedBadge;
  feedback: string;
  iteration: number;
}

interface BadgeSaveRequest {
  badge: GeneratedBadge;
  courseId: string;
  badgeData: BadgeFormData;
}

/**
 * Generate badge using AI
 * POC: Returns mock SVG badge, replace with actual API call
 */
export async function generateBadge(request: BadgeGenerationRequest): Promise<GeneratedBadge> {
  try {
    // TODO: Replace with actual API call to backend
    // const response = await apiClient.post('/api/ai-extensions/badges/generate', request);
    
    // Mock API delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Generate title and description from form data
    const title = generateBadgeTitle(request.formData);
    const description = generateBadgeDescription(request.formData);
    
    // Generate mock SVG badge
    const mockSvg = generateMockBadgeSVG(title);
    
    return {
      id: `badge-${Date.now()}`,
      title,
      description,
      image: mockSvg,
      metadata: {
        scope: request.formData.scope,
        unitId: request.formData.unitId,
        style: request.formData.style,
        tone: request.formData.tone,
        level: request.formData.level,
        criterion: request.formData.criterion,
        skillsEnabled: request.formData.skillsEnabled,
        userDescription: request.formData.description,
      },
    };
  } catch (error) {
    throw new Error(`Failed to generate badge: ${error}`);
  }
}

/**
 * Refine badge based on user feedback
 * POC: Returns slightly modified SVG, replace with actual AI refinement call
 */
export async function refineBadge(request: BadgeRefinementRequest): Promise<GeneratedBadge> {
  try {
    // TODO: Replace with actual API call to backend
    // const response = await apiClient.post('/api/ai-extensions/badges/refine', request);
    
    // Mock API delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Generate refined mock SVG (slightly different)
    const refinedSvg = generateMockBadgeSVG(request.generatedBadge.title, request.iteration);
    
    return {
      ...request.generatedBadge,
      id: `badge-${Date.now()}`,
      image: refinedSvg,
      metadata: {
        ...request.generatedBadge.metadata,
        lastFeedback: request.feedback,
      },
    };
  } catch (error) {
    throw new Error(`Failed to refine badge: ${error}`);
  }
}

/**
 * Save badge to course files
 * POC: Logs save request, replace with actual file save API call
 */
export async function saveBadge(request: BadgeSaveRequest): Promise<string> {
  try {
    // TODO: Replace with actual API call to backend
    // const response = await apiClient.post('/api/ai-extensions/badges/save', request);
    // return response.data.filePath;
    
    // Mock API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Return mock file path
    const filePath = `/course/${request.courseId}/badges/${request.badge.id}.svg`;
    
    console.log('Badge saved to:', filePath);
    console.log('Badge data:', {
      id: request.badge.id,
      title: request.badge.title,
      description: request.badge.description,
      scope: request.badgeData.scope,
      style: request.badgeData.style,
      tone: request.badgeData.tone,
      level: request.badgeData.level,
      criterion: request.badgeData.criterion,
      filePath,
    });
    
    return filePath;
  } catch (error) {
    throw new Error(`Failed to save badge: ${error}`);
  }
}

/**
 * Generate badge title from form data
 * POC: Creates title based on level and criterion
 */
function generateBadgeTitle(formData: BadgeFormData): string {
  const levelNames: Record<string, string> = {
    beginner: 'Starter',
    intermediate: 'Proficient',
    advanced: 'Expert',
    expert: 'Master',
  };

  const criterionNames: Record<string, string> = {
    completion: 'Completion',
    mastery: 'Mastery',
    participation: 'Participation',
    excellence: 'Excellence',
  };

  const level = levelNames[formData.level] || formData.level;
  const criterion = criterionNames[formData.criterion] || formData.criterion;

  return `${level} ${criterion}`;
}

/**
 * Generate badge description from form data
 * POC: Creates description based on scope and selected options
 */
function generateBadgeDescription(formData: BadgeFormData): string {
  const scopeNames: Record<string, string> = {
    course: 'this course',
    section: 'this section',
    unit: 'this unit',
  };

  const toneNames: Record<string, string> = {
    professional: 'professional',
    friendly: 'friendly and approachable',
    academic: 'academic',
    creative: 'creative and innovative',
  };

  const scope = scopeNames[formData.scope] || formData.scope;
  const tone = toneNames[formData.tone] || formData.tone;

  let description = `Awarded for ${formData.criterion} in ${scope} with a ${tone} appearance.`;
  
  if (formData.skillsEnabled) {
    description += ' Skills will be extracted and aligned.';
  }

  return description;
}

/**
 * Generate a mock SVG badge for POC
 * In production, this would be replaced with AI-generated or designed badges
 */
function generateMockBadgeSVG(title: string, iteration: number = 0): string {
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];
  const color = colors[iteration % colors.length];
  
  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240">
      <!-- Outer circle (badge background) -->
      <defs>
        <linearGradient id="badge-gradient-${iteration}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:${color};stop-opacity:1" />
          <stop offset="100%" style="stop-color:#333333;stop-opacity:1" />
        </linearGradient>
      </defs>
      
      <!-- Main circle -->
      <circle cx="100" cy="100" r="90" fill="url(#badge-gradient-${iteration})" stroke="#333" stroke-width="3"/>
      
      <!-- Inner content -->
      <circle cx="100" cy="100" r="80" fill="white" opacity="0.1"/>
      
      <!-- Star/emblem fill -->
      <g transform="translate(100, 85)" fill="white">
        <polygon points="0,-30 8,-8 32,-8 12,8 20,30 0,14 -20,30 -12,8 -32,-8 -8,-8" />
      </g>
      
      <!-- Badge title -->
      <text x="100" y="160" text-anchor="middle" font-size="16" font-weight="bold" fill="${color}" font-family="Arial, sans-serif" text-overflow="ellipsis">
        ${title.substring(0, 15)}
      </text>
      
      <!-- Ribbon at bottom -->
      <path d="M 40 190 L 40 220 L 100 210 L 160 220 L 160 190" fill="${color}" opacity="0.7" stroke="${color}" stroke-width="2"/>
      
      <!-- Iteration indicator (for POC) -->
      ${iteration > 0 ? `<text x="100" y="235" text-anchor="middle" font-size="10" fill="#666" font-family="Arial">v${iteration}</text>` : ''}
    </svg>
  `;
}

/**
 * Get human-in-loop metrics (POC implementation)
 * In production, this would fetch from analytics/logging backend
 */
export async function getHumanInLoopMetrics(courseId: string) {
  try {
    // TODO: Replace with actual metrics API call
    // const response = await apiClient.get(`/api/ai-extensions/metrics/badges/${courseId}`);
    
    // Mock response
    return {
      totalSessions: 12,
      totalIterations: 45,
      averageIterationsPerBadge: 3.75,
      feedbackPatterns: {
        'color change': 8,
        'style adjustment': 5,
        'wording clarification': 3,
        'symbol addition': 2,
      },
      commonRefinements: [
        'Make more professional looking',
        'Adjust colors',
        'Add relevant symbols',
      ],
      averageTimePerSession: 450, // seconds
      acceptanceRate: 0.92, // 92% of generated badges are saved
    };
  } catch (error) {
    console.error('Failed to fetch metrics:', error);
    throw error;
  }
}
