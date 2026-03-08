import React, { useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button, Card, Badge, Form, Spinner, Stack,
} from '@openedx/paragon';
import QuestionEditor from './QuestionEditor';
import messages from '../messages';
import { useLibraryCreatorContext } from '../context/LibraryCreatorContext';
import { Choice } from '../hooks/useLibraryCreator';

const PROBLEM_TYPE_LABELS: Record<string, string> = {
  multiplechoiceresponse: 'Single Choice',
  choiceresponse: 'Multiple Choice',
  optionresponse: 'Dropdown',
  numericalresponse: 'Numeric',
  stringresponse: 'Text',
};

/** Choice list — shared by MCQ, checkbox, and dropdown */
const ChoiceList = ({ choices }: { choices: Choice[] }) => {
  const intl = useIntl();
  return (
    <ul className="list-unstyled small mb-0">
      {choices.map((choice, i) => (
        // eslint-disable-next-line react/no-array-index-key
        <li key={i} className={`d-flex align-items-start mb-1 ${choice.isCorrect ? 'text-success' : 'text-muted'}`}>
          <span className="mr-2" style={{ minWidth: '1rem' }}>
            {choice.isCorrect ? '✓' : '○'}
          </span>
          <span>
            {choice.text}
            {choice.feedback && (
              <span className="ml-2 font-italic text-info" style={{ fontSize: '0.75rem' }}>
                ({choice.feedback})
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
};

/** Labelled field row */
const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="mb-2">
    <span className="small font-weight-bold text-muted text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>
      {label}
    </span>
    <div className="small mt-1">{children}</div>
  </div>
);

const QuestionCard = ({ index }: { index: number }) => {
  const {
    questions,
    questionHistories,
    selectedVersionIndices,
    discardedIndices,
    regeneratingIndices,
    editingIndex,
    regenerateQuestion,
    selectVersion,
    updateQuestion,
    discardQuestion,
    restoreQuestion,
    setEditingIndex,
  } = useLibraryCreatorContext();

  const intl = useIntl();
  const [showRegenerateForm, setShowRegenerateForm] = useState(false);
  const [regenerateInstructions, setRegenerateInstructions] = useState('');

  const question = questions[index];
  const history = questionHistories[index] || [question];
  const selectedVersionIndex = selectedVersionIndices[index] ?? 0;
  const isDiscarded = discardedIndices.has(index);
  const isRegenerating = regeneratingIndices.has(index);
  const isEditing = editingIndex === index;

  const typeLabel = PROBLEM_TYPE_LABELS[question.problemType] || question.problemType;
  const isChoiceBased = ['multiplechoiceresponse', 'choiceresponse', 'optionresponse'].includes(question.problemType);
  const isNumeric = question.problemType === 'numericalresponse';
  const isText = question.problemType === 'stringresponse';

  return (
    <Card
      className={`question-card mb-2 ${isDiscarded ? 'question-card--discarded' : ''}`}
      style={{ position: 'relative', opacity: isDiscarded ? 0.5 : 1 }}
    >
      {/* Regenerating overlay */}
      {isRegenerating && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(255,255,255,0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2,
            borderRadius: 'inherit',
          }}
        >
          <Spinner animation="border" size="sm" role="status" />
          <span className="ml-2 small">
            {intl.formatMessage(messages['ai.library.creator.card.regenerating'])}
          </span>
        </div>
      )}

      {/* ── Header ── */}
      <Card.Section>
        <div className="d-flex align-items-center justify-content-between">
          <span className="font-weight-bold small flex-1">
            {index + 1}. {question.displayName}
          </span>
          <Badge pill variant="info" className="ml-2 small">
            {typeLabel}
          </Badge>
        </div>
      </Card.Section>

      <Card.Divider />

      {/* ── Question body ── */}
      <Card.Section>

        {/* Question text */}
        <Field label={intl.formatMessage(messages['ai.library.creator.card.field.question'])}>
          {/* eslint-disable-next-line react/no-danger */}
          <div dangerouslySetInnerHTML={{ __html: question.questionHtml }} />
        </Field>

        {/* Choice-based answers */}
        {isChoiceBased && question.choices && question.choices.length > 0 && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.choices'])}>
            <ChoiceList choices={question.choices} />
          </Field>
        )}

        {/* Numeric answer + tolerance */}
        {isNumeric && (
          <div className="d-flex" style={{ gap: '1.5rem' }}>
            {question.answerValue && (
              <Field label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}>
                <code>{question.answerValue}</code>
              </Field>
            )}
            {question.tolerance && question.tolerance !== '<UNKNOWN>' && (
              <Field label={intl.formatMessage(messages['ai.library.creator.card.field.tolerance'])}>
                <code>±{question.tolerance}</code>
              </Field>
            )}
          </div>
        )}

        {/* Text / string answer */}
        {isText && question.answerValue && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.answer'])}>
            <code>{question.answerValue}</code>
          </Field>
        )}

        {/* Explanation */}
        {question.explanation && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.explanation'])}>
            <span className="text-muted">{question.explanation}</span>
          </Field>
        )}

        {/* Demand hints */}
        {question.demandHints && question.demandHints.length > 0 && (
          <Field label={intl.formatMessage(messages['ai.library.creator.card.field.hints'])}>
            <ol className="pl-3 mb-0 small text-muted">
              {question.demandHints.map((hint, i) => (
                // eslint-disable-next-line react/no-array-index-key
                <li key={i}>{hint}</li>
              ))}
            </ol>
          </Field>
        )}

        {/* Version history navigator */}
        {history.length > 1 && (
          <div className="d-flex align-items-center mt-2" style={{ gap: '0.25rem' }}>
            <Button
              variant="link"
              size="sm"
              className="p-0"
              aria-label={intl.formatMessage(messages['ai.library.creator.card.version.previous'])}
              disabled={selectedVersionIndex === 0}
              onClick={() => selectVersion(index, selectedVersionIndex - 1)}
            >
              ‹
            </Button>
            <span className="small text-muted">
              {intl.formatMessage(messages['ai.library.creator.card.version.counter'], {
                current: selectedVersionIndex + 1,
                total: history.length,
              })}
            </span>
            <Button
              variant="link"
              size="sm"
              className="p-0"
              aria-label={intl.formatMessage(messages['ai.library.creator.card.version.next'])}
              disabled={selectedVersionIndex === history.length - 1}
              onClick={() => selectVersion(index, selectedVersionIndex + 1)}
            >
              ›
            </Button>
          </div>
        )}

        {/* Action buttons */}
        {!isDiscarded ? (
          <>
            <Stack direction="horizontal" gap={1} className="mt-2">
              <Button
                variant="outline-primary"
                size="sm"
                onClick={() => setEditingIndex(isEditing ? null : index)}
                disabled={isRegenerating || showRegenerateForm}
              >
                {intl.formatMessage(messages['ai.library.creator.card.edit'])}
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => setShowRegenerateForm((v) => !v)}
                disabled={isRegenerating}
              >
                {intl.formatMessage(messages['ai.library.creator.card.regenerate'])}
              </Button>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => discardQuestion(index)}
                disabled={isRegenerating || showRegenerateForm}
              >
                {intl.formatMessage(messages['ai.library.creator.card.discard'])}
              </Button>
            </Stack>

            {/* Inline regenerate form */}
            {showRegenerateForm && (
              <div className="regenerate-form border-top mt-2 pt-2">
                <Form.Group controlId={`regen-instructions-${index}`} className="mb-1">
                  <Form.Label className="small">
                    {intl.formatMessage(messages['ai.library.creator.card.regenerate.instructions.label'])}
                  </Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    size="sm"
                    value={regenerateInstructions}
                    onChange={(e) => setRegenerateInstructions(e.target.value)}
                    placeholder={intl.formatMessage(messages['ai.library.creator.card.regenerate.instructions.placeholder'])}
                  />
                </Form.Group>
                <Stack direction="horizontal" gap={1}>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      setShowRegenerateForm(false);
                      regenerateQuestion(index, regenerateInstructions || undefined);
                      setRegenerateInstructions('');
                    }}
                  >
                    {intl.formatMessage(messages['ai.library.creator.card.regenerate.confirm'])}
                  </Button>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={() => { setShowRegenerateForm(false); setRegenerateInstructions(''); }}
                  >
                    {intl.formatMessage(messages['ai.library.creator.cancel'])}
                  </Button>
                </Stack>
              </div>
            )}
          </>
        ) : (
          <div className="mt-2">
            <span className="badge badge-secondary mr-2">
              {intl.formatMessage(messages['ai.library.creator.card.discarded.label'])}
            </span>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => restoreQuestion(index)}
            >
              {intl.formatMessage(messages['ai.library.creator.card.restore'])}
            </Button>
          </div>
        )}

        {/* Inline editor */}
        {isEditing && !isDiscarded && (
          <QuestionEditor
            question={question}
            onSave={(updated) => { updateQuestion(index, updated); setEditingIndex(null); }}
            onCancel={() => setEditingIndex(null)}
          />
        )}
      </Card.Section>
    </Card>
  );
};

export default QuestionCard;
