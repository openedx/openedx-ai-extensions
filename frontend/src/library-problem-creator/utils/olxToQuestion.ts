/**
 * Parse an OLX (XML) problem string back into a Question JSON object.
 *
 * Mirrors the structure produced by the backend's json_to_olx Jinja template.
 * Parsing is done with text/html for robustness (handles HTML content inside
 * the OLX that might not be well-formed XML).
 */
import { Choice, Question } from '../types';

const TAG_TO_TYPE: Record<string, string> = {
  multiplechoiceresponse: 'multiplechoiceresponse',
  choiceresponse: 'choiceresponse',
  optionresponse: 'optionresponse',
  numericalresponse: 'numericalresponse',
  stringresponse: 'stringresponse',
};

export interface OlxParseResult {
  question: Question;
  parseError?: string;
}

/** Return the first direct-child element whose tag matches */
function directChild(el: Element, tag: string): Element | null {
  for (let i = 0; i < el.children.length; i++) {
    if (el.children[i].tagName.toLowerCase() === tag) {
      return el.children[i];
    }
  }
  return null;
}

function parseChoiceElements(responseEl: Element): Choice[] {
  return Array.from(responseEl.querySelectorAll('choice')).map((c) => {
    const textDiv = c.querySelector('div');
    const feedback = c.querySelector('choicehint div')?.textContent?.trim();
    return {
      text: textDiv?.textContent?.trim() || c.childNodes[0]?.textContent?.trim() || '',
      isCorrect: c.getAttribute('correct') === 'true',
      ...(feedback ? { feedback } : {}),
    };
  });
}

function parseOptionElements(responseEl: Element): Choice[] {
  return Array.from(responseEl.querySelectorAll('option')).map((opt) => {
    const feedback = opt.querySelector('optionhint div')?.textContent?.trim();
    // Clone and strip hints to get clean text
    const clone = opt.cloneNode(true) as Element;
    clone.querySelectorAll('optionhint').forEach((h) => h.remove());
    return {
      text: clone.textContent?.trim() || '',
      isCorrect: opt.getAttribute('correct') === 'true',
      ...(feedback ? { feedback } : {}),
    };
  });
}

/**
 * Convert an OLX string to a Question object.
 * Returns the parsed question and an optional parseError string
 * if parsing failed (in which case question is the fallback).
 */
export function olxToQuestion(olxString: string, fallback: Question): OlxParseResult {
  if (!olxString.trim()) {
    return { question: fallback, parseError: 'OLX string is empty' };
  }

  try {
    const doc = new DOMParser().parseFromString(
      `<!DOCTYPE html><html><body>${olxString}</body></html>`,
      'text/html',
    );

    const problem = doc.querySelector('problem');
    if (!problem) {
      return { question: fallback, parseError: 'No <problem> element found in OLX' };
    }

    const displayName = problem.getAttribute('display_name') || fallback.displayName;

    // The question HTML lives in the first direct <div> child of <problem>
    const topDiv = directChild(problem, 'div');
    let questionHtml = topDiv?.innerHTML?.trim() || fallback.questionHtml;

    let { problemType } = fallback;
    let choices: Choice[] = fallback.choices ?? [];
    let { answerValue } = fallback;
    let { tolerance } = fallback;

    const matchedEntry = Object.entries(TAG_TO_TYPE).find(
      ([tag]) => problem.querySelector(tag) !== null,
    );

    if (matchedEntry) {
      const [tag, type] = matchedEntry;
      const responseEl = problem.querySelector(tag)!;
      problemType = type;

      if (type === 'multiplechoiceresponse' || type === 'choiceresponse') {
        choices = parseChoiceElements(responseEl);
      } else if (type === 'optionresponse') {
        choices = parseOptionElements(responseEl);
      } else if (type === 'numericalresponse') {
        answerValue = responseEl.getAttribute('answer') ?? undefined;
        const toleranceEl = responseEl.querySelector('responseparam[type="tolerance"]');
        tolerance = toleranceEl?.getAttribute('default') ?? undefined;
      } else if (type === 'stringresponse') {
        answerValue = responseEl.getAttribute('answer') ?? undefined;
        // For stringresponse the question is in <label>
        const labelEl = responseEl.querySelector('label');
        if (labelEl) {
          questionHtml = labelEl.innerHTML?.trim() || questionHtml;
        }
      }
    }

    // Explanation: second <p> inside .detailed-solution
    let { explanation } = fallback;
    const solutionPs = problem.querySelectorAll('solution .detailed-solution p');
    if (solutionPs.length >= 2) {
      explanation = solutionPs[1]?.textContent?.trim() || explanation;
    }

    // Demand hints
    const hintDivs = problem.querySelectorAll('demandhint hint div');
    const demandHints = Array.from(hintDivs)
      .map((h) => h.textContent?.trim() || '')
      .filter(Boolean);

    return {
      question: {
        ...fallback,
        displayName,
        questionHtml,
        problemType,
        choices,
        answerValue,
        tolerance,
        explanation,
        demandHints: demandHints.length > 0 ? demandHints : fallback.demandHints,
      },
    };
  } catch (err) {
    return { question: fallback, parseError: `OLX parse error: ${(err as Error).message}` };
  }
}
