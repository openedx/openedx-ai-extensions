/**
 * Parse an OLX (XML) problem string back into a Question JSON object.
 *
 * Mirrors the structure produced by the backend's json_to_olx Jinja template.
 * Parsing is done with text/html for robustness (handles HTML content inside
 * the OLX that might not be well-formed XML).
 */
import { Choice, Question } from '../../types';

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
const directChild = (el: Element, tag: string): Element | null => {
  for (let i = 0; i < el.children.length; i++) {
    if (el.children[i].tagName.toLowerCase() === tag) {
      return el.children[i];
    }
  }
  return null;
};

const parseChoiceElements = (responseEl: Element): Choice[] => Array.from(responseEl.querySelectorAll('choice')).map((c) => {
  const textDiv = c.querySelector('div');
  const feedback = c.querySelector('choicehint div')?.textContent?.trim();
  return {
    text: textDiv?.textContent?.trim() || c.childNodes[0]?.textContent?.trim() || '',
    isCorrect: c.getAttribute('correct') === 'true',
    ...(feedback ? { feedback } : {}),
  };
});

const parseOptionElements = (responseEl: Element): Choice[] => Array.from(responseEl.querySelectorAll('option')).map((opt) => {
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

/**
 * Convert an OLX string to a Question object.
 * Returns the parsed question and an optional parseError string
 * if parsing failed (in which case question is the fallback).
 */
export const olxToQuestion = (olxString: string, fallback: Question): OlxParseResult => {
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
};

/** Serialize question for the JSON editor, omitting the derived olx field */
export const questionToJson = (question: Question): string => {
  const { olx, ...rest } = question;
  return JSON.stringify(rest, null, 2);
};

/**
 * Convert Question JSON back to OLX XML string.
 * Parses existing OLX and updates it with values from the Question object.
 */
export const questionToOlx = (question: Question, currentOlxString?: string): string => {
  if (!currentOlxString || !currentOlxString.trim()) {
    return ''; // Can't generate from scratch without a template
  }

  try {
    // Parse raw OLX (no DOCTYPE wrapper)
    const doc = new DOMParser().parseFromString(currentOlxString, 'application/xml');
    const problem = doc.querySelector('problem');
    if (!problem) {
      return currentOlxString;
    }

    // Update display name
    problem.setAttribute('display_name', question.displayName);

    // Update question text (first <div> child)
    const topDiv = directChild(problem, 'div');
    if (topDiv) {
      topDiv.innerHTML = question.questionHtml;
    }

    // Remove old response elements
    ['multiplechoiceresponse', 'choiceresponse', 'optionresponse', 'numericalresponse', 'stringresponse'].forEach((type) => {
      const old = problem.querySelector(type);
      if (old) { old.remove(); }
    });

    // Create appropriate response element
    const {
      problemType, choices, answerValue, tolerance,
    } = question;
    if (problemType === 'multiplechoiceresponse' || problemType === 'choiceresponse') {
      const responseEl = document.createElement(problemType);
      responseEl.setAttribute('type', 'MultipleChoice');
      const choiceGroupEl = document.createElement('choicegroup');
      choiceGroupEl.setAttribute('type', problemType === 'choiceresponse' ? 'MultipleSelection' : 'SingleSelection');

      choices.forEach((choice) => {
        const choiceEl = document.createElement('choice');
        choiceEl.setAttribute('correct', choice.isCorrect ? 'true' : 'false');
        const divEl = document.createElement('div');
        divEl.textContent = choice.text;
        choiceEl.appendChild(divEl);
        if (choice.feedback) {
          const hintEl = document.createElement('choicehint');
          const hintDiv = document.createElement('div');
          hintDiv.textContent = choice.feedback;
          hintEl.appendChild(hintDiv);
          choiceEl.appendChild(hintEl);
        }
        choiceGroupEl.appendChild(choiceEl);
      });
      responseEl.appendChild(choiceGroupEl);
      problem.appendChild(responseEl);
    } else if (problemType === 'optionresponse') {
      const responseEl = document.createElement('optionresponse');
      choices.forEach((choice) => {
        const optEl = document.createElement('option');
        optEl.setAttribute('correct', choice.isCorrect ? 'true' : 'false');
        optEl.textContent = choice.text;
        if (choice.feedback) {
          const hintEl = document.createElement('optionhint');
          const hintDiv = document.createElement('div');
          hintDiv.textContent = choice.feedback;
          hintEl.appendChild(hintDiv);
          optEl.appendChild(hintEl);
        }
        responseEl.appendChild(optEl);
      });
      problem.appendChild(responseEl);
    } else if (problemType === 'numericalresponse') {
      const responseEl = document.createElement('numericalresponse');
      if (answerValue) {
        responseEl.setAttribute('answer', answerValue);
      }
      if (tolerance && tolerance !== '<UNKNOWN>') {
        const paramEl = document.createElement('responseparam');
        paramEl.setAttribute('type', 'tolerance');
        paramEl.setAttribute('default', tolerance);
        responseEl.appendChild(paramEl);
      }
      const textlineEl = document.createElement('textline');
      responseEl.appendChild(textlineEl);
      problem.appendChild(responseEl);
    } else if (problemType === 'stringresponse') {
      const responseEl = document.createElement('stringresponse');
      if (answerValue) {
        responseEl.setAttribute('answer', answerValue);
      }
      responseEl.setAttribute('type', 'ci');
      const labelEl = document.createElement('label');
      labelEl.textContent = question.questionHtml;
      responseEl.appendChild(labelEl);
      const textlineEl = document.createElement('textline');
      textlineEl.setAttribute('size', '20');
      responseEl.appendChild(textlineEl);
      problem.appendChild(responseEl);
    }

    // Update solution/explanation
    let solutionEl = problem.querySelector('solution');
    if (solutionEl) { solutionEl.remove(); }
    if (question.explanation) {
      solutionEl = document.createElement('solution');
      const detailedSolEl = document.createElement('div');
      detailedSolEl.className = 'detailed-solution';
      const pTitle = document.createElement('p');
      pTitle.textContent = 'Explanation';
      detailedSolEl.appendChild(pTitle);
      const pExpl = document.createElement('p');
      pExpl.textContent = question.explanation;
      detailedSolEl.appendChild(pExpl);
      solutionEl.appendChild(detailedSolEl);
      problem.appendChild(solutionEl);
    }

    // Update demand hints
    let demandHintEl = problem.querySelector('demandhint');
    if (demandHintEl) { demandHintEl.remove(); }
    if (question.demandHints && question.demandHints.length > 0) {
      demandHintEl = document.createElement('demandhint');
      question.demandHints.forEach((hint) => {
        const hintEl = document.createElement('hint');
        const divEl = document.createElement('div');
        divEl.textContent = hint;
        hintEl.appendChild(divEl);
        demandHintEl!.appendChild(hintEl);
      });
      problem.appendChild(demandHintEl);
    }

    // Serialize back to string
    return new XMLSerializer().serializeToString(problem);
  } catch {
    return currentOlxString; // Return original on error
  }
};
