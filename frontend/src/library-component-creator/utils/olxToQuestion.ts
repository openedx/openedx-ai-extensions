/**
 * Parse an OLX (XML) problem string back into a Question JSON object.
 *
 * Mirrors the structure produced by the backend's json_to_olx Jinja template.
 * Parsing is done with text/html for robustness (handles HTML content inside
 * the OLX that might not be well-formed XML).
 */
import { Choice, Question } from '../hooks/useLibraryCreator';

const TAG_TO_TYPE: Record<string, string> = {
  multiplechoiceresponse: 'multiplechoiceresponse',
  choiceresponse: 'choiceresponse',
  optionresponse: 'optionresponse',
  numericalresponse: 'numericalresponse',
  stringresponse: 'stringresponse',
};

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
 * Returns the fallback Question unchanged if parsing fails.
 */
export function olxToQuestion(olxString: string, fallback: Question): Question {
  if (!olxString.trim()) {
    return fallback;
  }

  try {
    const doc = new DOMParser().parseFromString(
      `<!DOCTYPE html><html><body>${olxString}</body></html>`,
      'text/html',
    );

    const problem = doc.querySelector('problem');
    if (!problem) {
      return fallback;
    }

    const displayName = problem.getAttribute('display_name') || fallback.displayName;

    // The question HTML lives in the first direct <div> child of <problem>
    const topDiv = directChild(problem, 'div');
    let questionHtml = topDiv?.innerHTML?.trim() || fallback.questionHtml;

    let problemType = fallback.problemType;
    let choices: Choice[] = fallback.choices ?? [];
    let answerValue: string | undefined = fallback.answerValue;
    let tolerance: string | undefined = fallback.tolerance;

    for (const [tag, type] of Object.entries(TAG_TO_TYPE)) {
      const responseEl = problem.querySelector(tag);
      if (!responseEl) { continue; }

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
      break;
    }

    // Explanation: second <p> inside .detailed-solution
    let explanation: string | undefined = fallback.explanation;
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
      ...fallback,
      displayName,
      questionHtml,
      problemType,
      choices,
      answerValue,
      tolerance,
      explanation,
      demandHints: demandHints.length > 0 ? demandHints : fallback.demandHints,
    };
  } catch {
    return fallback;
  }
}
