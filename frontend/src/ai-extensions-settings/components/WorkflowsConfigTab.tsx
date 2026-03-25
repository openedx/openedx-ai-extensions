/**
 * WorkflowsConfigTab Component
 * Two-column layout: profile list on the left, detail view on the right.
 *
 * NOTE: syntax highlighting via CodeMirror is deferred until the module boundary
 * between this plugin and frontend-app-authoring is formalised (webpack alias needed
 * to avoid duplicate @codemirror/state instances).
 */

import { useEffect, useState } from 'react';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Alert, Badge, Button, Form, OverlayTrigger, Spinner, Tooltip,
} from '@openedx/paragon';
import { AIWorkflowProfile, PromptTemplate } from '../../types';
import {
  fetchProfilesList, fetchPromptTemplate, savePromptTemplate,
} from '../../services/profilesService';
import { prepareContextData } from '../../services/utils';
import messages from '../messages';

type ProfileView = 'profile' | 'scopes' | 'prompt';

const COLUMN_HEADER_HEIGHT = '2.75rem';

/** Scan processorConfig for the first promptTemplate value, returns null if absent. */
const getPromptTemplate = (effectiveConfig: Record<string, any>): string | null => {
  const processorConfig = effectiveConfig?.processorConfig ?? effectiveConfig?.processor_config;
  if (!processorConfig || typeof processorConfig !== 'object') { return null; }
  for (const processor of Object.values(processorConfig)) {
    const template = (processor as any)?.promptTemplate ?? (processor as any)?.prompt_template;
    if (template) { return String(template); }
  }
  return null;
};

/** Relative time label with full date on hover. */
const RelativeDate = ({ dateStr }: { dateStr: string }) => {
  const date = new Date(dateStr);
  const diffMs = Date.now() - date.getTime();
  const diffSeconds = Math.round(diffMs / 1000);

  let value: number;
  let unit: Intl.RelativeTimeFormatUnit;
  if (diffSeconds < 60) { value = -diffSeconds; unit = 'second'; } else if (diffSeconds < 3600) { value = -Math.round(diffSeconds / 60); unit = 'minute'; } else if (diffSeconds < 86400) { value = -Math.round(diffSeconds / 3600); unit = 'hour'; } else if (diffSeconds < 2592000) { value = -Math.round(diffSeconds / 86400); unit = 'day'; } else if (diffSeconds < 31536000) { value = -Math.round(diffSeconds / 2592000); unit = 'month'; } else { value = -Math.round(diffSeconds / 31536000); unit = 'year'; }

  const relative = new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(value, unit);
  const full = date.toLocaleString();

  return (
    <OverlayTrigger placement="top" overlay={<Tooltip id={`date-${dateStr}`}>{full}</Tooltip>}>
      <span style={{ cursor: 'help', textDecoration: 'underline dotted' }}>{relative}</span>
    </OverlayTrigger>
  );
};

/** Structured editor for a PromptTemplate. */
const PromptView = ({ data, identifier }: { data: PromptTemplate; identifier: string }) => {
  const [body, setBody] = useState(data.body);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const isDirty = body !== data.body;

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await savePromptTemplate({ identifier, body });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setSaveError('Failed to save prompt. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4" style={{ overflowY: 'auto', flex: 1 }}>
      <div className="d-flex mb-3" style={{ gap: '1rem' }}>
        <Form.Group className="flex-grow-1 mb-0">
          <Form.Label className="small text-muted mb-1">ID</Form.Label>
          <Form.Control value={data.id} readOnly size="sm" className="font-monospace" />
        </Form.Group>
        <Form.Group className="flex-grow-1 mb-0">
          <Form.Label className="small text-muted mb-1">Slug</Form.Label>
          <Form.Control value={data.slug} readOnly size="sm" />
        </Form.Group>
      </div>

      <div className="d-flex mb-4 small" style={{ gap: '2rem' }}>
        <div>
          <span className="text-muted mr-2">Created</span>
          <RelativeDate dateStr={data.createdAt} />
        </div>
        <div>
          <span className="text-muted mr-2">Updated</span>
          <RelativeDate dateStr={data.updatedAt} />
        </div>
      </div>

      <Form.Group className="mb-3">
        <Form.Label>Prompt body</Form.Label>
        <Form.Control
          as="textarea"
          rows={12}
          value={body}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setBody(e.target.value)}
          style={{ resize: 'vertical', lineHeight: 1.6 }}
        />
      </Form.Group>

      {saveError && <Alert variant="danger" className="mb-2">{saveError}</Alert>}

      <div className="d-flex justify-content-end align-items-center" style={{ gap: '0.75rem' }}>
        {saved && <span className="small text-success">Saved!</span>}
        <Button
          variant="primary"
          size="sm"
          onClick={handleSave}
          disabled={saving || !isDirty}
        >
          {saving ? <><Spinner animation="border" size="sm" className="mr-2" />Saving…</> : 'Save'}
        </Button>
      </div>
    </div>
  );
};

/** Read-only JSON viewer. */
const JsonViewer = ({ content }: { content: string }) => (
  <pre
    className="bg-white m-0 p-4 small"
    style={{
      flex: 1,
      fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
      lineHeight: 1.6,
      overflowY: 'auto',
      whiteSpace: 'pre',
    }}
  >{content}
  </pre>
);

interface ProfileListItemProps {
  profile: AIWorkflowProfile;
  isSelected: boolean;
  onSelect: (p: AIWorkflowProfile) => void;
}

const ProfileListItem = ({ profile, isSelected, onSelect }: ProfileListItemProps) => {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      type="button"
      onClick={() => onSelect(profile)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`px-3 py-3 w-100 text-left border-0 border-bottom ${isSelected ? 'bg-primary text-white' : ''}`}
      style={{
        background: (!isSelected && hovered) ? 'var(--pgn-color-gray-200)' : undefined,
        borderLeft: `3px solid ${isSelected ? 'var(--pgn-color-primary-base)' : 'transparent'}`,
        cursor: 'pointer',
        transition: 'background 0.1s',
      }}
    >
      <div className="font-weight-bold small mb-1">{profile.slug}</div>
      {profile.description && (
        <div
          className="x-small text-muted"
          style={{
            lineHeight: '1.35',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {profile.description}
        </div>
      )}
    </button>
  );
};

const WorkflowsConfigTab = () => {
  const intl = useIntl();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<AIWorkflowProfile[]>([]);
  const [selected, setSelected] = useState<AIWorkflowProfile | null>(null);
  const [view, setView] = useState<ProfileView>('profile');
  const [promptData, setPromptData] = useState<PromptTemplate | null>(null);
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptError, setPromptError] = useState<string | null>(null);

  const handleSelectProfile = (profile: AIWorkflowProfile) => {
    setSelected(profile);
    setView('profile');
    setPromptData(null);
    setPromptError(null);
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchProfilesList({ contextData: prepareContextData({}), signal: controller.signal })
      .then((data) => {
        setProfiles(data.profiles);
        if (data.profiles.length > 0) { setSelected(data.profiles[0]); }
        setLoading(false);
      })
      .catch((err) => {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') { return; }
        setError(intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.error']));
        setLoading(false);
      });
    return () => controller.abort();
  }, [intl]);

  useEffect(() => {
    if (view !== 'prompt' || !selected) { return undefined; }
    const identifier = getPromptTemplate(selected.effectiveConfig);
    if (!identifier) { return undefined; }

    const controller = new AbortController();
    setPromptLoading(true);
    setPromptError(null);

    fetchPromptTemplate({ identifier, signal: controller.signal })
      .then((data) => { setPromptData(data); setPromptLoading(false); })
      .catch((err) => {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') { return; }
        setPromptError(intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.error']));
        setPromptLoading(false);
      });

    return () => controller.abort();
  }, [view, selected, intl]);

  if (loading) {
    return (
      <div className="p-4 d-flex align-items-center">
        <Spinner animation="border" size="sm" />
        <span className="ml-2">
          {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.loading'])}
        </span>
      </div>
    );
  }

  if (error) {
    return <div className="p-4"><Alert variant="danger">{error}</Alert></div>;
  }

  if (profiles.length === 0) {
    return (
      <div className="p-4">
        <Alert variant="info">
          {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.empty'])}
        </Alert>
      </div>
    );
  }

  const configJson = selected ? JSON.stringify(selected.effectiveConfig, null, 2) : '';
  const scopesJson = selected ? JSON.stringify(selected.scopes, null, 2) : '';
  const promptTemplate = selected ? getPromptTemplate(selected.effectiveConfig) : null;

  const renderPromptContent = () => {
    if (promptLoading) {
      return (
        <div className="p-4 d-flex align-items-center">
          <Spinner animation="border" size="sm" />
          <span className="ml-2">Loading prompt…</span>
        </div>
      );
    }
    if (promptError) {
      return <div className="p-4"><Alert variant="danger">{promptError}</Alert></div>;
    }
    if (promptData) {
      return <PromptView data={promptData} identifier={promptTemplate!} />;
    }
    return null;
  };

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: '520px' }}>

      {/* Left column */}
      <div
        className="border-right d-flex flex-column"
        style={{ width: '260px', flexShrink: 0 }}
      >
        <div
          className="bg-light border-bottom d-flex align-items-center px-3"
          style={{ height: COLUMN_HEADER_HEIGHT, flexShrink: 0 }}
        >
          <span className="x-small text-uppercase text-muted font-weight-bold" style={{ letterSpacing: '0.07em' }}>
            {intl.formatMessage(messages['openedx-ai-extensions.settings-modal.workflows.profiles.title'])}
          </span>
          <Badge className="ml-2" variant="secondary">{profiles.length}</Badge>
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {profiles.map((profile) => (
            <ProfileListItem
              key={profile.id}
              profile={profile}
              isSelected={selected?.id === profile.id}
              onSelect={handleSelectProfile}
            />
          ))}
        </div>
      </div>

      {/* Right column */}
      <div className="d-flex flex-column" style={{ flex: 1, overflow: 'hidden' }}>
        {selected && (
          <>
            <div
              className="bg-light border-bottom d-flex align-items-center px-4"
              style={{ height: COLUMN_HEADER_HEIGHT, flexShrink: 0, gap: '0.5rem' }}
            >
              <span className="font-weight-bold mr-3">{selected.slug}</span>
              {(['profile', 'scopes', 'prompt'] as ProfileView[]).map((v) => (
                <Button
                  key={v}
                  size="sm"
                  variant={view === v ? 'primary' : 'tertiary'}
                  onClick={() => setView(v)}
                  className="text-capitalize"
                  disabled={v === 'prompt' && !promptTemplate}
                >
                  {v}
                </Button>
              ))}
            </div>

            <div style={{
              flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column',
            }}
            >
              {view === 'profile' && <JsonViewer content={configJson} />}
              {view === 'scopes' && <JsonViewer content={scopesJson} />}
              {view === 'prompt' && renderPromptContent()}
            </div>
          </>
        )}
      </div>

    </div>
  );
};

export default WorkflowsConfigTab;
