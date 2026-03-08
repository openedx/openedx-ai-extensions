export type CreatorStep = 'idle' | 'generating' | 'review' | 'preloaded' | 'saving' | 'error';

export interface Choice {
  text: string;
  isCorrect: boolean;
  feedback?: string;
}

/** Shape returned by the backend json_to_olx utility */
export interface Olx {
  category: string;
  data: string;
}

export interface Question {
  displayName: string;
  questionHtml: string;
  problemType: string;
  choices: Choice[];
  answerValue?: string;
  tolerance?: string;
  explanation?: string;
  demandHints?: string[];
  olx?: Olx;
}
