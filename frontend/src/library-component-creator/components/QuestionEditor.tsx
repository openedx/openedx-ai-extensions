import React, { useRef, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Button, Stack, Tab, Tabs,
} from '@openedx/paragon';
import { Question } from '../hooks/useLibraryCreator';
import { olxToQuestion } from '../utils/olxToQuestion';
import { useLibraryCreatorContext } from '../context/LibraryCreatorContext';
import messages from '../messages';

type EditorMode = 'olx' | 'json';

interface QuestionEditorProps {
  question: Question;
  onSave: (updated: Question) => void;
  onCancel: () => void;
}

/** Serialize question for the JSON editor, omitting the derived olx field */
function questionToJson(q: Question): string {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { olx, ...rest } = q;
  return JSON.stringify(rest, null, 2);
}

const QuestionEditor = ({ question, onSave, onCancel }: QuestionEditorProps) => {
  const intl = useIntl();
  const { CodeEditor } = useLibraryCreatorContext();
  const [mode, setMode] = useState<EditorMode>('olx');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleTabSelect = (key: any) => { if (key) { setMode(key as EditorMode); } };

  // Ref used to read the current value from the uncontrolled CodeMirror editor
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const editorRef = useRef<any>(undefined);

  // Fallback textarea state (used only when CodeEditor is not provided)
  const [olxText, setOlxText] = useState(question.olx?.data ?? '');
  const [jsonText, setJsonText] = useState(() => questionToJson(question));
  const [jsonError, setJsonError] = useState('');

  const handleApply = () => {
    if (mode === 'olx') {
      // CodeMirror 6 exposes current content via editorRef.current.state.doc.toString()
      const currentOlx = CodeEditor
        ? (editorRef.current?.state.doc.toString() ?? question.olx?.data ?? '')
        : olxText;
      const parsed = olxToQuestion(currentOlx, question);
      onSave({ ...parsed, olx: { category: 'problem', ...question.olx, data: currentOlx } });
    } else {
      try {
        const parsed = JSON.parse(jsonText);
        setJsonError('');
        onSave({ ...question, ...parsed });
      } catch {
        setJsonError(intl.formatMessage(messages['ai.library.creator.editor.json.error']));
      }
    }
  };

  return (
    <div className="question-editor border-top pt-3 mt-2">
      <Tabs
        variant="tabs"
        activeKey={mode}
        onSelect={handleTabSelect}
        id="question-editor-tabs"
      >
        <Tab
          eventKey="olx"
          title={intl.formatMessage(messages['ai.library.creator.editor.tab.olx'])}
        >
          <div className="pt-3">
            <p className="small text-muted mb-2">
              {intl.formatMessage(messages['ai.library.creator.editor.tab.olx.hint'])}
            </p>
            {CodeEditor ? (
              <CodeEditor 
              innerRef={editorRef}
              value={question.olx?.data ?? ''}
              />
            ) : (
              <textarea
                className="form-control form-control-sm"
                style={{ fontFamily: 'monospace', fontSize: '0.8rem', minHeight: '260px' }}
                value={olxText}
                onChange={(e) => setOlxText(e.target.value)}
                spellCheck={false}
              />
            )}
          </div>
        </Tab>

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
            <textarea
              className="form-control form-control-sm"
              style={{ fontFamily: 'monospace', fontSize: '0.8rem', minHeight: '260px' }}
              value={jsonText}
              onChange={(e) => { setJsonText(e.target.value); setJsonError(''); }}
              spellCheck={false}
            />
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
