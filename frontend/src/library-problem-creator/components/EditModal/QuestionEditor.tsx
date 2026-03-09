import { useRef, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import { logInfo } from '@edx/frontend-platform/logging';
import {
  Alert, Button, Form, Stack, Tab, Tabs,
} from '@openedx/paragon';
import { useLibraryProblemCreatorContext } from '../../context/LibraryProblemCreatorContext';
import { Question } from '../../types';
import { olxToQuestion, questionToJson, questionToOlx } from './utils';
import messages from '../../messages';

type EditorMode = 'olx' | 'json';

interface QuestionEditorProps {
  question: Question;
  onSave: (updated: Question) => void;
  onCancel: () => void;
}

const QuestionEditor = ({ question, onSave, onCancel }: QuestionEditorProps) => {
  const intl = useIntl();
  const { CodeEditor } = useLibraryProblemCreatorContext();
  const [mode, setMode] = useState<EditorMode>('json');
  const handleTabSelect = (key:string) => { if (key) { setMode(key as EditorMode); } };

  // Ref used to read the current value from the uncontrolled CodeMirror editor
  const editorRef = useRef<string>(undefined);

  // Fallback textarea state (used only when CodeEditor is not provided)
  const [olxText, setOlxText] = useState(question.olx?.data ?? '');
  const [jsonText, setJsonText] = useState(() => questionToJson(question));
  const [jsonError, setJsonError] = useState('');
  const [olxWarning, setOlxWarning] = useState('');

  const handleApply = () => {
    if (mode === 'olx') {
      // CodeMirror 6 exposes current content via editorRef.current.state.doc.toString()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const currentOlx = CodeEditor
        ? ((editorRef.current as any)?.state?.doc?.toString() ?? question.olx?.data ?? '')
        : olxText;
      const { question: parsed, parseError } = olxToQuestion(currentOlx, question);
      if (parseError) {
        setOlxWarning(parseError);
        logInfo('QuestionEditor: OLX parse warning:', parseError);
      } else {
        setOlxWarning('');
      }
      onSave({ ...parsed, olx: { category: 'problem', ...question.olx, data: currentOlx } });
    } else {
      try {
        const parsed = JSON.parse(jsonText);
        setJsonError('');
        // Sync OLX with JSON changes
        const updatedQuestion = { ...question, ...parsed };
        const updatedOlx = question.olx?.data
          ? questionToOlx(updatedQuestion, question.olx.data)
          : undefined;
        onSave({
          ...updatedQuestion,
          ...(updatedOlx ? { olx: { category: 'problem', ...question.olx, data: updatedOlx } } : {}),
        });
      } catch {
        setJsonError(intl.formatMessage(messages['ai.library.creator.editor.json.error']));
      }
    }
  };

  return (
    <div className="question-editor pt-3 mt-2">
      <Tabs
        variant="tabs"
        activeKey={mode}
        onSelect={handleTabSelect}
        id="question-editor-tabs"
      >
        <Tab
          eventKey="json"
          title={intl.formatMessage(messages['ai.library.creator.editor.tab.json'])}
        >
          <div className="pt-3">
            <p className="small text-muted mb-2">
              {intl.formatMessage(messages['ai.library.creator.editor.tab.json.hint'])}
            </p>
            {jsonError && (
              <Alert variant="danger" dismissible onClose={() => setJsonError('')} className="mb-2">
                {jsonError}
              </Alert>
            )}
            <Form.Group>
              <Form.Control
                as="textarea"
                value={jsonText}
                onChange={(e) => { setJsonText(e.target.value); setJsonError(''); }}
                spellCheck={false}
                rows={50}
              />
            </Form.Group>
          </div>
        </Tab>
        <Tab
          eventKey="olx"
          title={intl.formatMessage(messages['ai.library.creator.editor.tab.olx'])}
        >
          <div className="pt-3">
            <p className="small text-muted mb-2">
              {intl.formatMessage(messages['ai.library.creator.editor.tab.olx.hint'])}
            </p>
            {olxWarning && (
              <Alert variant="warning" dismissible onClose={() => setOlxWarning('')} className="mb-2">
                {olxWarning}
              </Alert>
            )}
            {CodeEditor ? (
              <div className="border">
                <CodeEditor
                  innerRef={editorRef}
                  value={question.olx?.data ?? ''}
                />
              </div>
            ) : (
              <Form.Group>
                <Form.Control
                  as="textarea"
                  value={olxText}
                  onChange={(e) => setOlxText(e.target.value)}
                  spellCheck={false}
                  rows={50}
                />
              </Form.Group>
            )}
          </div>
        </Tab>
      </Tabs>

      <Stack gap={2} direction="horizontal" className="mt-3">
        <Button variant="primary" size="sm" onClick={handleApply}>
          {intl.formatMessage(messages['ai.library.creator.editor.apply'])}
        </Button>
        <Button variant="outline-secondary" size="sm" onClick={onCancel}>
          {intl.formatMessage(messages['ai.library.creator.editor.cancel'])}
        </Button>
      </Stack>
    </div>
  );
};

export default QuestionEditor;
